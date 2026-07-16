/** Composer modes that may speak a final answer without tool/run milestones. */

export type AnswerNarrationComposerMode = 'ask' | 'plan';

export function isAnswerNarrationComposerMode(
  mode: string | null | undefined,
): mode is AnswerNarrationComposerMode {
  const normalized = String(mode || '')
    .trim()
    .toLowerCase();
  return normalized === 'ask' || normalized === 'plan';
}

/**
 * Ask/Plan speak only a final answer excerpt. They must never receive tool,
 * edit, thinking, or progress milestone narration.
 */
export function shouldNarrateAnswerCompletion(input: {
  mode: string | null | undefined;
  narration: 'off' | 'minimal' | 'conversational';
}): boolean {
  if (input.narration === 'off') {
    return false;
  }
  return isAnswerNarrationComposerMode(input.mode);
}
