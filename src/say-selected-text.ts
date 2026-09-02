import { Detail, getSelectedText } from "@raycast/api";
import { createElement, useEffect, useState } from "react";
import { formatStatus, getTtsStatus, say } from "./tts-api";

export default function Command() {
  const [markdown, setMarkdown] = useState("# Qwen TTS\n\nReading selected text…");
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
          setMarkdown("# Qwen TTS\n\nServer is not running.");
          setLoading(false);
        }
      }
    }

    async function run() {
      let text: string;

      try {
        text = (await getSelectedText()).trim();
      } catch {
        setMarkdown("# Say Selected Text\n\nNo text selected.");
        setLoading(false);
        return;
      }

      if (!text) {
        setMarkdown("# Say Selected Text\n\nNo text selected.");
        setLoading(false);
        return;
      }

      try {
        const response = await say(text);

        if (response.status === 409) {
          setMarkdown("# Say Selected Text\n\nAnother speech job is already running.");
        } else if (response.status === 503) {
          setMarkdown("# Say Selected Text\n\nModel is still starting…");
        } else if (!response.ok) {
          setMarkdown(`# Say Selected Text\n\nServer returned ${response.status}.`);
          setLoading(false);
          return;
        }

        await refresh();
        timer = setInterval(refresh, 500);
      } catch {
        setMarkdown("# Qwen TTS\n\nServer is not running.");
        setLoading(false);
      }
    }

    void run();

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, []);

  return createElement(Detail, { markdown, isLoading: loading });
}
