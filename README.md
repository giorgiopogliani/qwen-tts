# Qwen TTS

Minimal Raycast extension for speaking selected text with a local Qwen3-TTS model.

It exposes exactly two commands:

- **Say Selected Text**
- **Stop Running Say**

The Raycast commands talk to a small daemon on `127.0.0.1:8765`. The daemon is installed as a macOS LaunchAgent, starts at login, keeps the model loaded, streams audio as it is generated, and only accepts one speech job at a time.

## Model

Default:

```text
mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit
```

Default speaker is `Ryan` and language is `auto`.

## Install

Requires Apple Silicon, Raycast, Node.js, and Python 3.

```bash
git clone https://github.com/giorgiopogliani/qwen-tts.git
cd qwen-tts
bash scripts/install-daemon.sh
npm install
npm run dev
```

The first daemon start downloads the model. Later logins start it automatically and keep it warm.

Daemon logs are written to:

```text
~/Library/Logs/qwen-tts/server.log
```

Health check:

```bash
curl http://127.0.0.1:8765/health
```

## Configuration

The daemon supports these environment variables:

```text
QWEN_TTS_MODEL
QWEN_TTS_SPEAKER
QWEN_TTS_LANGUAGE
QWEN_TTS_STREAMING_INTERVAL
QWEN_TTS_PORT
```
