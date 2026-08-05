export type VaxonExecutiveComposerMode = 'ask' | 'dispatch';

const MISSION_PREFIX_RE = /^\s*(?:#{1,4}\s*)?mission(?:\s+(?:specification|id|title))?\s*:/i;

/** Keep an explicit mission envelope for the Dispatch route without changing Ask text. */
export function buildVaxonComposerSubmission(
  content: string,
  mode: VaxonExecutiveComposerMode,
): string {
  const trimmed = content.trim();
  if (!trimmed || mode === 'ask' || MISSION_PREFIX_RE.test(trimmed)) {
    return trimmed;
  }
  return `Mission:\n${trimmed}`;
}

/** The visual mode is also the transport safety boundary. */
export function vaxonComposerSubmissionIntent(
  mode: VaxonExecutiveComposerMode,
): 'ask' | 'dispatch' {
  return mode === 'ask' ? 'ask' : 'dispatch';
}

/** Enter sends; Shift+Enter reserves a new line for success criteria and constraints. */
export function shouldSubmitVaxonComposer(event: {
  key: string;
  shiftKey: boolean;
  isComposing?: boolean;
}): boolean {
  return event.key === 'Enter' && !event.shiftKey && !event.isComposing;
}
