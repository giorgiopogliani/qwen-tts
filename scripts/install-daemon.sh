#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/qwen-tts"
VENV="$APP_DIR/venv"
LOG_DIR="$HOME/Library/Logs/qwen-tts"
PLIST="$HOME/Library/LaunchAgents/com.giorgiopogliani.qwen-tts.plist"
LABEL="com.giorgiopogliani.qwen-tts"

mkdir -p "$APP_DIR" "$LOG_DIR" "$HOME/Library/LaunchAgents"
cp "$ROOT_DIR/server/qwen_tts_server.py" "$APP_DIR/server.py"

if command -v uv >/dev/null 2>&1; then
  uv venv --clear "$VENV"
  uv pip install --python "$VENV/bin/python" mlx-audio lingua-language-detector
else
  python3 -m venv --clear "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install mlx-audio lingua-language-detector
fi

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$VENV/bin/python</string>
    <string>$APP_DIR/server.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/server.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/server.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Qwen TTS daemon installed and started."
echo "Logs: $LOG_DIR/server.log"
