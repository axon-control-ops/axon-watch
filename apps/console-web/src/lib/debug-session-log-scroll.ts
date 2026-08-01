/** Pin-to-bottom helpers for the Debug Mode runtime log feed. */

export function isDebugLogPinnedToBottom(
  el: Pick<HTMLElement, 'scrollTop' | 'clientHeight' | 'scrollHeight'>,
  thresholdPx = 48,
): boolean {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= thresholdPx;
}

export function scrollDebugLogToBottom(
  el: Pick<HTMLElement, 'scrollTop' | 'scrollHeight'>,
): number {
  el.scrollTop = el.scrollHeight;
  return el.scrollTop;
}
