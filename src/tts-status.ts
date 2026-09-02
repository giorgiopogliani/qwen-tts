import { Detail } from "@raycast/api";
import { createElement, useEffect, useState } from "react";
import { formatStatus, getTtsStatus } from "./tts-api";

export default function Command() {
  const [markdown, setMarkdown] = useState("# Qwen TTS Status\n\nConnecting…");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      try {
        const status = await getTtsStatus();
        if (!cancelled) {
          setMarkdown(formatStatus(status, "Qwen TTS Status"));
          setLoading(status.phase === "starting");
        }
      } catch {
        if (!cancelled) {
          setMarkdown("# Qwen TTS Status\n\nServer is not running.");
          setLoading(false);
        }
      }
    }

    void refresh();
    const timer = setInterval(refresh, 500);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return createElement(Detail, { markdown, isLoading: loading });
}
