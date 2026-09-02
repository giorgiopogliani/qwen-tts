import { Detail, getSelectedText } from "@raycast/api";
import { useEffect, useState } from "react";
import { formatStatus, getTtsStatus, say } from "./tts-api";

export default function Command() {
  const [markdown, setMarkdown] = useState("# Say Selected Text\n\nStarting…");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | undefined;

    async function refresh() {
      try {
        const status = await getTtsStatus();
        if (!cancelled) {
          setMarkdown(formatStatus(status, "Say Selected Text"));
          setLoading(status.phase === "starting" || status.busy);
        }
      } catch {
        if (!cancelled) {
          setMarkdown("# Say Selected Text\n\nQwen TTS server is not running.");
          setLoading(false);
        }
      }
    }

    async function run() {
      try {
        const text = (await getSelectedText()).trim();
        if (!text) {
          setMarkdown("# Say Selected Text\n\nNo text selected.");
          setLoading(false);
          return;
        }

        const response = await say(text);
        if (response.status === 409) {
          setMarkdown("# Say Selected Text\n\nAnother speech job is already running.");
          setLoading(false);
          return;
        }
        if (response.status === 503) {
          setMarkdown("# Say Selected Text\n\nModel is still starting…");
        } else if (!response.ok) {
          setMarkdown(`# Say Selected Text\n\nServer returned ${response.status}.`);
          setLoading(false);
          return;
        }

        await refresh();
        timer = setInterval(refresh, 500);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setMarkdown(`# Say Selected Text\n\n${message || "Failed to read selected text."}`);
        setLoading(false);
      }
    }

    void run();

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, []);

  return <Detail markdown={markdown} isLoading={loading} />;
}
