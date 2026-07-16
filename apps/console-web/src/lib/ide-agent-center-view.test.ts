import { describe, expect, it } from 'vitest';

import {
  buildIdeAgentReviewBar,
  buildIdeAgentReviewComposerLabel,
  buildIdeAgentThreadStatusLabel,
  collectIdeAgentEditSummariesFromThread,
  extractIdeAgentEditSummaries,
  resolveActiveIdeAgentMessage,
  shouldShowIdeAgentReviewStrip,
  shouldShowIdeAgentThreadStatusStrip,
} from './ide-agent-center-view';

describe('ide agent center view', () => {
  it('prefers the streaming agent message', () => {
    const messages = [
      { message_id: 'm1', role: 'operator', content: 'fix it' },
      { message_id: 'm2', role: 'agent', content: 'older' },
      { message_id: 'm3', role: 'agent', content: 'live' },
    ];

    expect(
      resolveActiveIdeAgentMessage(messages, true, 'm3')?.message_id,
    ).toBe('m3');
  });

  it('extracts edit summaries from transcript blocks', () => {
    const edits = extractIdeAgentEditSummaries(
      [':::edit src/app.ts +3 -1', '+line', ':::'].join('\n'),
      'm1',
    );
    expect(edits).toHaveLength(1);
    expect(edits[0]?.path).toBe('src/app.ts');
    expect(edits[0]?.added).toBe(3);
  });

  it('normalizes absolute edit paths for workspace file open', () => {
    const edits = extractIdeAgentEditSummaries(
      ':::edit /home/edp/.cursor/projects/foo/README.md +1 -0\n+line\n:::\n',
      'm1',
    );
    expect(edits).toHaveLength(1);
    expect(edits[0]?.path).toBe('README.md');
  });

  it('shows the review strip while the agent is busy or review is ready', () => {
    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'ide',
        agentStreamActive: true,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 0,
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'operator',
        agentStreamActive: true,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 0,
      }),
    ).toBe(false);

    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'ide',
        agentStreamActive: false,
        composerAgentBusy: false,
        reviewReadyCount: 1,
        editedFileCount: 2,
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'ide',
        agentStreamActive: false,
        composerAgentBusy: false,
        reviewReadyCount: 1,
        editedFileCount: 0,
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'ide',
        agentStreamActive: false,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 2,
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentReviewStrip({
        layoutMode: 'ide',
        agentStreamActive: false,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 53,
        latestAgentTurnFailed: true,
      }),
    ).toBe(false);
  });

  it('builds thread status labels with VAXON prefix while streaming', () => {
    expect(
      buildIdeAgentThreadStatusLabel({
        activityLabel:
          'I need to review my previous answer for factual mistakes, missing steps, unsupported assumption…',
      }),
    ).toBe(
      'VAXON — I need to review my previous answer for factual mistakes, missing steps, unsupported assumption…',
    );

    expect(
      buildIdeAgentThreadStatusLabel({
        activityLabel: 'VAXON — Checking the file',
      }),
    ).toBe('VAXON — Checking the file');
  });

  it('shows thread status only while streaming in IDE mode', () => {
    expect(
      shouldShowIdeAgentThreadStatusStrip({
        layoutMode: 'ide',
        agentStreamActive: true,
        activityLabel: 'VAXON — Thinking…',
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentThreadStatusStrip({
        layoutMode: 'operator',
        agentStreamActive: true,
        activityLabel: 'VAXON — Thinking…',
      }),
    ).toBe(false);
  });

  it('builds composer review labels without VAXON thinking text', () => {
    expect(
      buildIdeAgentReviewComposerLabel({
        agentStreamActive: true,
        executionAccess: 'full',
        editedFileCount: 46,
        reviewReadyCount: 0,
        expanded: false,
      }),
    ).toBe('▸ 46 files');

    expect(
      buildIdeAgentReviewComposerLabel({
        agentStreamActive: true,
        executionAccess: 'full',
        editedFileCount: 0,
        reviewReadyCount: 0,
        expanded: false,
      }),
    ).toBe('Full Access — streaming runtime output…');

    expect(
      buildIdeAgentReviewComposerLabel({
        agentStreamActive: true,
        executionAccess: 'consultative',
        editedFileCount: 0,
        reviewReadyCount: 0,
        expanded: false,
        mode: 'plan',
      }),
    ).toBe('Plan — streaming outline…');
  });

  it('builds review bar labels from file and review counts', () => {
    expect(
      buildIdeAgentReviewBar({
        canStop: true,
        stopping: false,
        editedFileCount: 2,
        reviewReadyCount: 1,
        completing: false,
      }),
    ).toMatchObject({
      showStop: true,
      showResume: false,
      showReview: true,
      showApplyAll: true,
      reviewLabel: 'Review 2 files',
      applyLabel: 'Apply all',
    });

    expect(
      buildIdeAgentReviewBar({
        canStop: false,
        stopping: false,
        canResume: true,
        resumeLabel: 'Continue',
        editedFileCount: 3,
        reviewReadyCount: 0,
        completing: false,
      }),
    ).toMatchObject({
      showStop: false,
      showResume: true,
      resumeLabel: 'Continue',
      showReview: true,
      reviewLabel: 'Review 3 files',
    });

    expect(
      buildIdeAgentReviewBar({
        canStop: false,
        stopping: false,
        editedFileCount: 0,
        reviewReadyCount: 0,
        completing: false,
      }).showStop,
    ).toBe(false);
  });
});
