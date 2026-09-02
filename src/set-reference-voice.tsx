import { Action, ActionPanel, Form, Toast, showToast } from "@raycast/api";
import { copyFile, mkdir, rename, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { extname, join, resolve } from "node:path";
import { useState } from "react";

const APP_DIR = join(homedir(), "Library", "Application Support", "qwen-tts");
const REFERENCE_AUDIO = join(APP_DIR, "reference.wav");
const REFERENCE_CONFIG = join(APP_DIR, "reference.json");

type Values = {
  audio: string[];
  transcript: string;
};

export default function Command() {
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(values: Values) {
    const source = values.audio[0];
    const transcript = values.transcript.trim();

    if (!source) {
      await showToast({ style: Toast.Style.Failure, title: "Choose a reference sample" });
      return;
    }

    if (extname(source).toLowerCase() !== ".wav") {
      await showToast({ style: Toast.Style.Failure, title: "Reference sample must be a WAV file" });
      return;
    }

    if (!transcript) {
      await showToast({ style: Toast.Style.Failure, title: "Enter the exact sample transcript" });
      return;
    }

    setIsLoading(true);

    try {
      await mkdir(APP_DIR, { recursive: true });

      if (resolve(source) !== resolve(REFERENCE_AUDIO)) {
        const audioTemp = `${REFERENCE_AUDIO}.tmp`;
        await copyFile(source, audioTemp);
        await rename(audioTemp, REFERENCE_AUDIO);
      }

      const configTemp = `${REFERENCE_CONFIG}.tmp`;
      await writeFile(configTemp, `${JSON.stringify({ ref_text: transcript }, null, 2)}\n`, "utf8");
      await rename(configTemp, REFERENCE_CONFIG);

      await showToast({ style: Toast.Style.Success, title: "Reference voice updated" });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await showToast({ style: Toast.Style.Failure, title: "Unable to save reference voice", message });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Set Reference Voice" onSubmit={handleSubmit} />
        </ActionPanel>
      }
    >
      <Form.FilePicker
        id="audio"
        title="Reference Audio"
        allowMultipleSelection={false}
        canChooseDirectories={false}
        canChooseFiles
      />
      <Form.TextArea
        id="transcript"
        title="Transcript"
        placeholder="Exact words spoken in the sample"
      />
    </Form>
  );
}
