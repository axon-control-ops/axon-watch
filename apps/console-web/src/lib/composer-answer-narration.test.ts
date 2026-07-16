import { describe, expect, it } from 'vitest';

import {
  isAnswerNarrationComposerMode,
  shouldNarrateAnswerCompletion,
} from './composer-answer-narration';
import { isToolCapableComposerMode } from './composer-tool-modes';

describe('composer answer narration', () => {
  it('allows ask and plan only', () => {
    expect(isAnswerNarrationComposerMode('ask')).toBe(true);
    expect(isAnswerNarrationComposerMode('plan')).toBe(true);
    expect(isAnswerNarrationComposerMode('agent')).toBe(false);
    expect(isAnswerNarrationComposerMode('debug')).toBe(false);
    expect(isAnswerNarrationComposerMode('kairo')).toBe(false);
  });

  it('keeps ask/plan non-tool-capable', () => {
    expect(isToolCapableComposerMode('ask')).toBe(false);
    expect(isToolCapableComposerMode('plan')).toBe(false);
    expect(isToolCapableComposerMode('agent')).toBe(true);
    expect(isToolCapableComposerMode('debug')).toBe(true);
  });

  it('gates answer completion by narration level', () => {
    expect(
      shouldNarrateAnswerCompletion({ mode: 'ask', narration: 'minimal' }),
    ).toBe(true);
    expect(
      shouldNarrateAnswerCompletion({ mode: 'plan', narration: 'conversational' }),
    ).toBe(true);
    expect(
      shouldNarrateAnswerCompletion({ mode: 'ask', narration: 'off' }),
    ).toBe(false);
    expect(
      shouldNarrateAnswerCompletion({ mode: 'agent', narration: 'minimal' }),
    ).toBe(false);
  });
});
