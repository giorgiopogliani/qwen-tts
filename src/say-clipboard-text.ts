import { Clipboard, launchCommand, LaunchType, showHUD } from "@raycast/api";
import { say } from "./tts-api";

async function openStatus() {
  await launchCommand({ name: "tts-status", type: LaunchType.UserInitiated });
}

export default async function Command() {
  const text = ((await Clipboard.readText()) ?? "").trim();

  if (!text) {
    await showHUD("Clipboard is empty");
    return;
  }

  try {
    const response = await say(text);

    if (response.status === 409) {
      await openStatus();
      return;
    }

    if (!response.ok) {
      await showHUD(`Qwen TTS error (${response.status})`);
      return;
    }

    await openStatus();
  } catch {
    await showHUD("Qwen TTS server is not running");
  }
}
