type SubmitHandler = (content: string) => Promise<void>;

let submitHandler: SubmitHandler | null = null;

export function registerKairoConversationSubmit(handler: SubmitHandler): () => void {
  submitHandler = handler;
  return () => {
    if (submitHandler === handler) {
      submitHandler = null;
    }
  };
}

export async function submitKairoConversationTranscript(content: string): Promise<void> {
  const trimmed = content.trim();
  if (!trimmed || !submitHandler) {
    return;
  }
  await submitHandler(trimmed);
}
