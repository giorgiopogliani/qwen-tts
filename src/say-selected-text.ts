import { getSelectedText, showHUD } from "@raycast/api";

const SERVER = "http://127.0.0.1:8765";

export default async function Command() {
  let text: string;

  try {
    text = (await getSelectedText()).trim();
  } catch {
    await showHUD("No text selected");
    return;
  }

  if (!text) {
    await showHUD("No text selected");
    return;
  }

  try {
    const response = await fetch(`${SERVER}/say`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(2000),
    });

    if (response.status === 202) {
      await showHUD("Speaking");
      return;
    }

    if (response.status === 409) {
      await showHUD("Already speaking");
      return;
    }

    if (response.status === 503) {
      await showHUD("Qwen TTS is starting");
      return;
    }

    await showHUD("Qwen TTS error");
  } catch {
    await showHUD("Qwen TTS server is not running");
  }
}
