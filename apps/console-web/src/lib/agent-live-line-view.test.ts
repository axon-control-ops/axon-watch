import { describe, expect, it } from 'vitest';

import {
  collapseBackToBackThinkingEcho,
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  sanitizeAgentThinkingForOperator,
  truncateAgentLiveLineForDisplay,
} from './agent-live-line-view';

const LONG_THINKING =
  "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews without breaking layout.";

const DASHBOARD_THOUGHT =
  'I found the one concrete breakage left behind: the new teacher dashboard tests aren’t mocking useWindowDimensions, so they fail immediately, while the parent realtime tests already pass. I’m patching the test environment now so the new dashboard work can actually run.';

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

  it('collapses exact and glued back-to-back thinking echoes', () => {
    expect(sanitizeAgentThinkingForOperator(DASHBOARD_THOUGHT + DASHBOARD_THOUGHT)).toBe(
      DASHBOARD_THOUGHT,
    );
    const glued =
      'found the one concrete breakage left behind: the new teacher dashboard tests aren’t mocking useWindowDimensions, so they fail immediately, while the parent realtime tests already pass. I’m patching the test environment now so the new dashboard work can actually run.' +
      DASHBOARD_THOUGHT;
    expect(sanitizeAgentThinkingForOperator(glued)).toBe(DASHBOARD_THOUGHT);
  });

  it('collapses leading-apostrophe thinking echoes', () => {
    const body =
      "got the current README and the local setup docs open. I'm going to turn the root guide into a cleaner day-to-day entry point so it matches the actual workflow in this repo.";
    const echoed = `'ve ${body}I've ${body}`;
    expect(sanitizeAgentThinkingForOperator(echoed)).toBe(`I've ${body}`);
  });
});

describe('collapseBackToBackThinkingEcho', () => {
  it('keeps non-echoed thinking intact', () => {
    expect(collapseBackToBackThinkingEcho(DASHBOARD_THOUGHT)).toBe(DASHBOARD_THOUGHT);
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
  it('returns the first one or two complete sentences', () => {
    expect(firstSpeakableAgentLiveBlock(LONG_THINKING)).toBe(
      "I'm starting to analyze the rendering issues the user wants fixed. They want table rendering to work in markdown previews without breaking layout.",
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
