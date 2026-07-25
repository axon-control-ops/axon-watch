import { createRafStreamUiBatcher } from './stream-ui-raf-batch';

/** RAF-batch transcript content patches so Full Access streams do not thrash Vue. */
export function createStreamMessageContentBatcher(
  patch: (threadId: string, messageId: string, content: string) => void,
) {
  return createRafStreamUiBatcher<{ messageId: string; content: string }>((threadId, partial) => {
    patch(threadId, partial.messageId, partial.content);
  });
}
