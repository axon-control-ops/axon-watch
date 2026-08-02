export type VaxonExecutiveComposerMode = 'mission' | 'ask';

const MISSION_PREFIX_RE = /^\s*(?:#{1,4}\s*)?mission(?:\s+(?:specification|id|title))?\s*:/i;
const ASK_PREFIX_RE = /^\s*(?:what|why|when|where|who|how|can|could|should|is|are|do|does|show|explain|status|risk)\b/i;
const QUESTION_RE = /\?\s*$/;

/**
 * Default empty composer to Mission — VAXON is an operating system, not a chatbot.
 * Questions stay conversational; objectives become missions. Operators can still
 * flip the compact mode control when that inference is wrong.
 */
export function inferVaxonComposerMode(content: string): VaxonExecutiveComposerMode {
  const trimmed = content.trim();
  if (!trimmed) {
    return 'mission';
  }
  if (ASK_PREFIX_RE.test(trimmed) || QUESTION_RE.test(trimmed)) {
    return 'ask';
  }
  return 'mission';
}

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

export function shouldSubmitVaxonComposer(event: {
  key: string;
  shiftKey: boolean;
  isComposing?: boolean;
}): boolean {
  return event.key === 'Enter' && !event.shiftKey && !event.isComposing;
}
