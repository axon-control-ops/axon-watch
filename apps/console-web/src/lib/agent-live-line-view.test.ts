import { describe, expect, it } from 'vitest';

import {
  collapseBackToBackThinkingEcho,
  firstSpeakableAgentLiveBlock,
  isAgentLiveLineTruncated,
  isWaitProgressThinking,
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

  it('rewrites bare Thinking… lead-ins to I am thinking…', () => {
    expect(sanitizeAgentThinkingForOperator('Thinking…')).toBe('I am thinking…');
    expect(sanitizeAgentThinkingForOperator('Thinking...')).toBe('I am thinking…');
    expect(sanitizeAgentThinkingForOperator("thinking I'll check Sentry next.")).toBe(
      "I am thinking I'll check Sentry next.",
    );
    expect(sanitizeAgentThinkingForOperator('I am thinking about the next step.')).toBe(
      'I am thinking about the next step.',
    );
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

  it('strips trailing stream fence markers glued onto thinking', () => {
    expect(
      sanitizeAgentThinkingForOperator(
        'The Metro cache is active and the build is still progressing. :::',
      ),
    ).toBe('The Metro cache is active and the build is still progressing.');
  });
});

describe('isWaitProgressThinking', () => {
  it('detects wait/poll status chatter', () => {
    expect(
      isWaitProgressThinking(
        'The Metro cache is active and the build is still progressing.',
      ),
    ).toBe(true);
    expect(isWaitProgressThinking("I'm patching the dashboard tests now.")).toBe(false);
  });
});

describe('collapseBackToBackThinkingEcho', () => {
  it('keeps non-echoed thinking intact', () => {
    expect(collapseBackToBackThinkingEcho(DASHBOARD_THOUGHT)).toBe(DASHBOARD_THOUGHT);
  });

  it('collapses near-duplicate echoes with glued words and small wording drift', () => {
    const first =
      'You were clicking the right place. DashPro in the left Workspaces list, or theDASHPRO orb* in the middle — those are the intended targets. The detail panel was also telling you that click should open the workspace. What happened instead was only a camera zoom, because that open path was not wired up. fixed that: clicking a workspace in the list or on the orb now switches into the IDE for that workspace. Until the page reloads with this change, use theIDE tab in the top bar after selecting the workspace.';
    const second =
      'You were clicking the right place. DashPro in the left Workspaces list, or the DASHPRO orb in the middle — those are the intended targets. The detail panel was also telling you that click should open the workspace. What happened instead was only a camera zoom, because that open path was not wired up. I fixed that: clicking a workspace in the list or on the orb now switches into the IDE for that workspace. Until the page reloads with this change, use the IDE tab in the top bar after selecting the workspace.';
    expect(collapseBackToBackThinkingEcho(first + second)).toBe(second);
    expect(sanitizeAgentThinkingForOperator(first + second)).toBe(second);
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
