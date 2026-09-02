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
    "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit",
)
DEFAULT_LANGUAGE = os.getenv("QWEN_TTS_LANGUAGE", "Italian")
STREAMING_INTERVAL = float(os.getenv("QWEN_TTS_STREAMING_INTERVAL", "0.32"))
SUPPORTED_LANGUAGES = {"Italian", "English"}
APP_DIR = os.path.expanduser("~/Library/Application Support/qwen-tts")
REFERENCE_AUDIO = os.getenv(
    "QWEN_TTS_REFERENCE_AUDIO",
    os.path.join(APP_DIR, "reference.wav"),
)
REFERENCE_CONFIG = os.getenv(
    "QWEN_TTS_REFERENCE_CONFIG",
    os.path.join(APP_DIR, "reference.json"),
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("qwen-tts")


def reference_is_configured() -> bool:
    if not os.path.isfile(REFERENCE_AUDIO) or not os.path.isfile(REFERENCE_CONFIG):
        return False

    try:
        with open(REFERENCE_CONFIG, encoding="utf-8") as handle:
            config = json.load(handle)
        return bool(str(config.get("ref_text", "")).strip())
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def load_reference() -> tuple[str, str]:
    if not os.path.isfile(REFERENCE_AUDIO):
        raise RuntimeError("Reference audio is not configured")

    try:
        with open(REFERENCE_CONFIG, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Reference voice configuration is invalid") from exc

    ref_text = str(config.get("ref_text", "")).strip()
    if not ref_text:
        raise RuntimeError("Reference transcript is not configured")

    return REFERENCE_AUDIO, ref_text


class State:
    def __init__(self):
        self.ready = threading.Event()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.busy = False
        self.phase = "starting"
        self.current_text = None
        self.last_error = None
        self.current_language = DEFAULT_LANGUAGE
        self.jobs = queue.Queue(maxsize=1)
        self.player = None
        self.logs = deque(maxlen=50)

    def record(self, message: str):
        entry = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        with self.lock:
            self.logs.append(entry)
        log.info(message)

    def submit(self, text: str, language: str) -> str:
        if not self.ready.is_set():
            return "starting"

        with self.lock:
            if self.busy:
                return "busy"
            self.stop_event.clear()
            self.busy = True
            self.phase = "queued"
            self.current_text = text
            self.current_language = language
            self.last_error = None
            self.jobs.put_nowait((text, language))

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
                "language": self.current_language,
                "reference_configured": reference_is_configured(),
                "reference_audio": os.path.basename(REFERENCE_AUDIO)
                if os.path.isfile(REFERENCE_AUDIO)
                else None,
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
        text, language = state.jobs.get()
        try:
            ref_audio, ref_text = load_reference()
            generated_audio = False
            state.set_phase("generating")
            state.record(f"Language: {language}")
            state.record("Generating speech from reference voice")

            for result in model.generate(
                text=text,
                lang_code=language,
                ref_audio=ref_audio,
                ref_text=ref_text,
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
            self.send_json(
                200,
                {
                    "ready": status["ready"],
                    "busy": status["busy"],
                    "reference_configured": status["reference_configured"],
                },
            )
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
            language = payload.get("language", DEFAULT_LANGUAGE)
            if not text:
                raise ValueError("text is required")
            if language not in SUPPORTED_LANGUAGES:
                raise ValueError("unsupported language")
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_json(400, {"error": "invalid request"})
            return

        if not reference_is_configured():
            self.send_json(412, {"error": "reference voice is not configured"})
            return

        result = state.submit(text, language)
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
