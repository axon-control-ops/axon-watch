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

  if (lower.includes('timed out after')) {
    return raw.startsWith(action) ? raw : `${action}: ${raw}`;
  }

  if (error.name === 'AbortError') {
    return `${action} was cancelled.`;
  }

  return raw;
}
