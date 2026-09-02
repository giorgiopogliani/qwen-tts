import { Clipboard, launchCommand, LaunchType, showHUD } from "@raycast/api";
import { say, type TtsLanguage } from "./tts-api";

async function openCommand(name: "tts-status" | "set-reference-voice") {
  await launchCommand({ name, type: LaunchType.UserInitiated });
}

export default async function Command(props: { arguments?: { language?: string } }) {
  const text = ((await Clipboard.readText()) ?? "").trim();

  if (!text) {
    await showHUD("Clipboard is empty");
    return;
  }

  const language: TtsLanguage = props.arguments?.language === "English" ? "English" : "Italian";

  try {
    const response = await say(text, language);

    if (response.status === 412) {
      await openCommand("set-reference-voice");
      return;
    }

    if (response.status === 409) {
      await openCommand("tts-status");
      return;
    }

    if (!response.ok) {
      await showHUD(`Qwen TTS error (${response.status})`);
      return;
    }

    await openCommand("tts-status");
  } catch {
    await showHUD("Qwen TTS server is not running");
  }
}
