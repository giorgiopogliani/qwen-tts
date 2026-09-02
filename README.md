# Qwen TTS

Raycast extension for speaking selected or clipboard text with a local Qwen3-TTS model.

Commands:

- **Say Selected Text**
- **Say Clipboard Text**
- **Stop Running Say**
- **Set Reference Voice**
- **Qwen TTS Status**

The Raycast commands talk to a small daemon on `127.0.0.1:8765`. The daemon is installed as a macOS LaunchAgent, starts at login, keeps the model loaded, streams audio as it is generated, and only accepts one speech job at a time.

## Model

Default:

```text
mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit
```

The Base model clones a voice from a reference WAV sample. The reference is stored locally in:

```text
~/Library/Application Support/qwen-tts/reference.wav
```

Its transcript is stored next to it in `reference.json`.

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

After installation, run **Set Reference Voice** in Raycast. Choose a clean WAV sample and enter the exact words spoken in the sample. A short sample with one speaker and little background noise works best.

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
QWEN_TTS_LANGUAGE
QWEN_TTS_STREAMING_INTERVAL
QWEN_TTS_PORT
QWEN_TTS_REFERENCE_AUDIO
QWEN_TTS_REFERENCE_CONFIG
```
