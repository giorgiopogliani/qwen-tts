import { showHUD } from "@raycast/api";

const SERVER = "http://127.0.0.1:8765";

export default async function Command() {
  try {
    const response = await fetch(`${SERVER}/stop`, {
      method: "POST",
      signal: AbortSignal.timeout(2000),
    });

    await showHUD(response.ok ? "Stopped" : "Qwen TTS error");
  } catch {
    await showHUD("Qwen TTS server is not running");
  }
}
