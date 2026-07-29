/** Turn opaque browser/network failures into operator-readable copy. */
export function humanizeNetworkError(
  error: unknown,
  options: { action?: string } = {},
): string {
  const action = (options.action ?? 'Request').trim() || 'Request';
  if (!(error instanceof Error)) {
    return `${action} failed.`;
  }

  const raw = error.message.trim() || 'unknown error';
  const lower = raw.toLowerCase();

  if (
    lower === 'failed to fetch' ||
    lower.includes('networkerror') ||
    lower.includes('network request failed') ||
    lower.includes('load failed')
  ) {
    return (
      `${action} could not reach the control plane (network). ` +
      'Check that Axon-X is up on :8787 / the Vite proxy, then try again. ' +
      'If ./scripts/dev/check-health.sh is green, this was likely a brief restart blip — retry send.'
    );
  }

  if (
    lower.includes('control-plane unavailable') ||
    lower.includes('cp_down') ||
    /\b503\b/.test(lower)
  ) {
    return (
      `${action} hit a brief control-plane gap (:8787). ` +
      'Retry send in a moment — if it keeps failing, run ./scripts/dev/check-health.sh.'
    );
  }

  if (lower.includes('step-up') || lower.includes('step up confirmation')) {
    return (
      `${action} needs Full Access step-up (X-Axon-Step-Up). ` +
      'Keep Agent on FULL ACCESS and retry — if this persists, refresh the console session.'
    );
  }

  if (lower.includes('timed out after')) {
    return raw.startsWith(action) ? raw : `${action}: ${raw}`;
  }

  if (error.name === 'AbortError') {
    return `${action} was cancelled.`;
  }

  return raw;
}
