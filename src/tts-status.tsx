import { Detail } from "@raycast/api";
import { useEffect, useState } from "react";
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
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : String(error);
          setMarkdown(`# Qwen TTS Status\n\n${message || "Server is not running."}`);
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

  return <Detail markdown={markdown} isLoading={loading} />;
}
