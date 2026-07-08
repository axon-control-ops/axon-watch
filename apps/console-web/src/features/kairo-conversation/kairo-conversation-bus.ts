type SubmitHandler = (
  content: string,
  options?: KairoConversationSubmitOptions,
) => Promise<void>;

export type KairoConversationSubmitOptions = {
  voiceCaptureMode?: 'manual' | 'hands_free' | 'barge_in';
};

let submitHandler: SubmitHandler | null = null;

export function registerKairoConversationSubmit(handler: SubmitHandler): () => void {
  submitHandler = handler;
  return () => {
    if (submitHandler === handler) {
      submitHandler = null;
    }
  };
}

export async function submitKairoConversationTranscript(
  content: string,
  options?: KairoConversationSubmitOptions,
): Promise<void> {
  const trimmed = content.trim();
  if (!trimmed || !submitHandler) {
    return;
  }
  await submitHandler(trimmed, options);
}
