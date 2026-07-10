import { describe, expect, it } from 'vitest';

import {
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  sanitizeAgentThinkingForOperator,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';

const LONG_THINKING =
  "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews without breaking layout.";

describe('sanitizeAgentThinkingForOperator', () => {
  it('strips third-person user-asking meta commentary', () => {
    expect(sanitizeAgentThinkingForOperator('The user is asking whether')).toBe('');
    expect(sanitizeAgentThinkingForOperator('*The user is asking whether*')).toBe('');
    expect(
      sanitizeAgentThinkingForOperator(
        'The user is asking whether an image would show up here. Checking the image preview path.',
      ),
    ).toBe('Checking the image preview path.');
  });

  it('keeps technical thinking that only mentions the user incidentally', () => {
    expect(sanitizeAgentThinkingForOperator(LONG_THINKING)).toBe(LONG_THINKING);
  });
});

describe('truncateAgentLiveLineForDisplay', () => {
  it('prefers sentence boundaries over mid-word cuts', () => {
    const display = truncateAgentLiveLineForDisplay(LONG_THINKING, 96);
    expect(display.endsWith('…')).toBe(true);
    expect(display).not.toMatch(/\bto…$/);
    expect(display).toContain('rendering issues the user wants fixed.');
  });

  it('leaves short lines untouched', () => {
    expect(truncateAgentLiveLineForDisplay('Checking the file')).toBe('Checking the file');
  });
});

describe('firstSpeakableAgentLiveBlock', () => {
  it('returns the first complete sentence block', () => {
    expect(firstSpeakableAgentLiveBlock(LONG_THINKING)).toBe(
      "I'm starting to analyze the rendering issues the user wants fixed.",
    );
  });

  it('skips pure user-meta thinking', () => {
    expect(firstSpeakableAgentLiveBlock('The user is asking whether')).toBe('');
  });

  it('skips partial fragments without a sentence end', () => {
    expect(firstSpeakableAgentLiveBlock('They want table rendering to')).toBe('');
  });
});

describe('isAgentLiveLineTruncated', () => {
  it('detects when display copy is shorter than the source', () => {
    const display = truncateAgentLiveLineForDisplay(LONG_THINKING, 96);
    expect(isAgentLiveLineTruncated(LONG_THINKING, display)).toBe(true);
    expect(isAgentLiveLineTruncated('Short line', 'Short line')).toBe(false);
  });
});
