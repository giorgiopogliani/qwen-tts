const SERVER = "http://127.0.0.1:8765";

export type TtsLanguage = "Italian" | "English";

export type TtsStatus = {
  ready: boolean;
  busy: boolean;
  phase: string;
  current_text: string | null;
  last_error: string | null;
  logs: string[];
  model: string;
  language: string;
  reference_configured: boolean;
  reference_audio: string | null;
};

export async function getTtsStatus(): Promise<TtsStatus> {
  const response = await fetch(`${SERVER}/status`, {
    signal: AbortSignal.timeout(1500),
  });

  if (!response.ok) {
    throw new Error(`Server returned ${response.status}`);
  }

  return (await response.json()) as TtsStatus;
}

export async function say(text: string, language: TtsLanguage = "Italian"): Promise<Response> {
  return fetch(`${SERVER}/say`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, language }),
    signal: AbortSignal.timeout(2000),
  });
}

export function formatStatus(status: TtsStatus, heading = "Qwen TTS"): string {
  const phase = status.phase.charAt(0).toUpperCase() + status.phase.slice(1);
  const logs = status.logs.length
    ? status.logs.slice(-20).map((line) => line.replaceAll("`", "'")).join("\n")
    : "No logs yet";

  const currentText = status.current_text
    ? `\n### Current Text\n\n${status.current_text.slice(0, 500)}${status.current_text.length > 500 ? "…" : ""}\n`
    : "";

  const error = status.last_error ? `\n### Error\n\n${status.last_error}\n` : "";
  const reference = status.reference_configured
    ? `Configured${status.reference_audio ? ` (${status.reference_audio})` : ""}`
    : "Not configured";

  return `# ${heading}\n\n**Status:** ${phase}\n\n**Model:** ${status.model}\n\n**Language:** ${status.language}\n\n**Reference:** ${reference}\n${currentText}${error}\n### Recent Logs\n\n\`\`\`text\n${logs}\n\`\`\``;
}
