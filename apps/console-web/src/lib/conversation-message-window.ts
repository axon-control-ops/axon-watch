export const CONVERSATION_MESSAGE_WINDOW_SIZE = 40;

export interface ConversationMessageWindow<T> {
  items: T[];
  page: number;
  olderCount: number;
  newerCount: number;
}

/** Keep long-running employee threads readable without mounting years of transcript DOM. */
export function conversationMessageWindow<T>(
  messages: T[],
  requestedPage: number,
  pageSize = CONVERSATION_MESSAGE_WINDOW_SIZE,
): ConversationMessageWindow<T> {
  const safeSize = Math.max(1, Math.floor(pageSize));
  const maxPage = Math.max(0, Math.ceil(messages.length / safeSize) - 1);
  const page = Math.min(maxPage, Math.max(0, Math.floor(requestedPage)));
  const end = Math.max(0, messages.length - page * safeSize);
  const start = Math.max(0, end - safeSize);
  return {
    items: messages.slice(start, end),
    page,
    olderCount: start,
    newerCount: messages.length - end,
  };
}
