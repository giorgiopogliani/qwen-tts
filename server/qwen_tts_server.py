#!/usr/bin/env python3

import json
import logging
import os
import queue
import threading
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.getenv("QWEN_TTS_PORT", "8765"))
MODEL = os.getenv(
    "QWEN_TTS_MODEL",
    "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
)
SPEAKER = os.getenv("QWEN_TTS_SPEAKER", "Ryan")
LANGUAGE = os.getenv("QWEN_TTS_LANGUAGE", "auto")
STREAMING_INTERVAL = float(os.getenv("QWEN_TTS_STREAMING_INTERVAL", "0.32"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("qwen-tts")


class State:
    def __init__(self):
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.busy = False
        self.phase = "starting"
        self.current_text = None
        self.last_error = None
        self.jobs = queue.Queue(maxsize=1)
        self.player = None
        self.logs = deque(maxlen=50)

    def record(self, message: str):
        entry = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        with self.lock:
            self.logs.append(entry)
        log.info(message)

    def submit(self, text: str) -> str:
        if not self.ready.is_set():
            return "starting"

        with self.lock:
            if self.busy:
                return "busy"
            self.stop_event.clear()
            self.busy = True
            self.phase = "queued"
            self.current_text = text
            self.last_error = None
            self.jobs.put_nowait(text)

        self.record("Speech job accepted")
        return "accepted"

    def stop(self) -> bool:
        with self.lock:
            was_busy = self.busy
            if was_busy:
                self.stop_event.set()
                self.phase = "stopping"
            player = self.player

        if player is not None:
            player.flush()

        if was_busy:
            self.record("Stop requested")
        return was_busy

    def set_phase(self, phase: str):
        with self.lock:
            self.phase = phase

    def set_error(self, error: str):
        with self.lock:
            self.last_error = error
            self.phase = "error"

    def finish(self):
        with self.lock:
            self.busy = False
            self.current_text = None
            if self.phase != "error":
                self.phase = "idle"

    def status(self):
        with self.lock:
            return {
                "ready": self.ready.is_set(),
                "busy": self.busy,
                "phase": self.phase,
                "current_text": self.current_text,
                "last_error": self.last_error,
                "logs": list(self.logs),
                "model": MODEL,
                "speaker": SPEAKER,
                "language": LANGUAGE,
            }


state = State()


def tts_worker():
    try:
        from mlx_audio.sts.audio_player import AudioPlayer
        from mlx_audio.tts.utils import load_model

        state.record(f"Loading model {MODEL}")
        model = load_model(MODEL)
        sample_rate = int(getattr(model, "sample_rate", 24000) or 24000)
        player = AudioPlayer(sample_rate=sample_rate, start_buffer_seconds=0.32)
        state.player = player
        state.ready.set()
        state.set_phase("idle")
        state.record(f"Ready on http://{HOST}:{PORT}")
    except Exception as exc:
        state.set_error(str(exc))
        log.exception("Failed to initialize Qwen TTS")
        os._exit(1)

    while True:
        text = state.jobs.get()
        try:
            generated_audio = False
            state.set_phase("generating")
            state.record("Generating speech")

            for result in model.generate_custom_voice(
                text=text,
                speaker=SPEAKER,
                language=LANGUAGE,
                stream=True,
                streaming_interval=STREAMING_INTERVAL,
            ):
                if state.stop_event.is_set():
                    player.flush()
                    break

                if not generated_audio:
                    state.set_phase("playing")
                    state.record("Playback started")

                generated_audio = True
                player.queue_audio(result.audio)

            if generated_audio and not state.stop_event.is_set():
                player.start_if_buffered(force=True)
                player.wait_for_drain()
                state.record("Playback finished")
        except Exception as exc:
            state.set_error(str(exc))
            log.exception("TTS generation failed")
            state.record(f"Generation failed: {exc}")
        finally:
            if state.stop_event.is_set():
                player.flush()
                state.record("Playback stopped")
            state.finish()
            state.jobs.task_done()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            status = state.status()
            self.send_json(200, {"ready": status["ready"], "busy": status["busy"]})
            return

        if self.path == "/status":
            self.send_json(200, state.status())
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/stop":
            self.send_json(200, {"stopped": state.stop()})
            return

        if self.path != "/say":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("invalid body size")
            payload = json.loads(self.rfile.read(length))
            text = payload.get("text", "").strip()
            if not text:
                raise ValueError("text is required")
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "invalid request"})
            return

        result = state.submit(text)
        if result == "accepted":
            self.send_json(202, {"status": "accepted"})
        elif result == "busy":
            self.send_json(409, {"error": "already speaking"})
        else:
            self.send_json(503, {"error": "model is starting"})

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    threading.Thread(target=tts_worker, name="qwen-tts-worker", daemon=True).start()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
