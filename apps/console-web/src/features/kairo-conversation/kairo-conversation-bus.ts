type SubmitHandler = (
  content: string,
  options?: KairoConversationSubmitOptions,
) => Promise<void>;

export type KairoConversationSubmitOptions = {
  voiceCaptureMode?: 'manual' | 'hands_free' | 'barge_in';
};

export type KairoConversationSubmitDispatchResult = 'submitted' | 'queued' | 'ignored';

let submitHandlers: SubmitHandler[] = [];
let queuedSubmissions: Array<{
  content: string;
  options?: KairoConversationSubmitOptions;
}> = [];
let draining = false;

function activeSubmitHandler(): SubmitHandler | null {
  return submitHandlers.at(-1) ?? null;
}

async function drainQueuedSubmissions(): Promise<void> {
  if (draining || !activeSubmitHandler() || queuedSubmissions.length === 0) {
    return;
  }
  draining = true;
  try {
    while (queuedSubmissions.length > 0) {
      const handler = activeSubmitHandler();
      if (!handler) {
        break;
      }
      const next = queuedSubmissions.shift();
      if (!next) {
        break;
      }
      await handler(next.content, next.options);
    }
  } finally {
    draining = false;
  }
}

export function registerKairoConversationSubmit(handler: SubmitHandler): () => void {
  submitHandlers = [...submitHandlers, handler];
  void drainQueuedSubmissions();
  return () => {
    submitHandlers = submitHandlers.filter((entry) => entry !== handler);
  };
}

export async function submitKairoConversationTranscript(
  content: string,
  options?: KairoConversationSubmitOptions,
): Promise<KairoConversationSubmitDispatchResult> {
  const trimmed = content.trim();
  if (!trimmed) {
    return 'ignored';
  }
  const handler = activeSubmitHandler();
  if (!handler) {
    queuedSubmissions.push({ content: trimmed, options });
    return 'queued';
  }
  await handler(trimmed, options);
  return 'submitted';
}

/** Test helper — reset global bus state between cases. */
export function resetKairoConversationSubmitBusForTests(): void {
  submitHandlers = [];
  queuedSubmissions = [];
  draining = false;
}
