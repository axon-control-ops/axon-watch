/** Pure helpers for AgentDock / conversation-seam scroll routing. */

const SCROLLABLE_OVERFLOW = new Set(['auto', 'scroll', 'overlay']);

export function overflowYAllowsScroll(overflowY: string): boolean {
  return SCROLLABLE_OVERFLOW.has(overflowY.trim().toLowerCase());
}

export function elementCanScrollInDirection(
  input: {
    scrollTop: number;
    clientHeight: number;
    scrollHeight: number;
    overflowY: string;
  },
  deltaY: number,
  epsilonPx = 2,
): boolean {
  if (!overflowYAllowsScroll(input.overflowY)) {
    return false;
  }
  if (input.scrollHeight <= input.clientHeight + epsilonPx) {
    return false;
  }
  if (deltaY < 0) {
    return input.scrollTop > epsilonPx;
  }
  if (deltaY > 0) {
    return input.scrollTop + input.clientHeight < input.scrollHeight - epsilonPx;
  }
  return false;
}

export function isConversationNearBottom(
  el: Pick<HTMLElement, 'scrollTop' | 'clientHeight' | 'scrollHeight'>,
  thresholdPx = 72,
): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= thresholdPx;
}

export function pinConversationScrollToBottom(
  el: Pick<HTMLElement, 'scrollTop' | 'scrollHeight'>,
): void {
  el.scrollTop = el.scrollHeight;
}
