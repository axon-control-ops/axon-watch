import { describe, expect, it } from 'vitest';

import {
  buildIdeAgentReviewBar,
  extractIdeAgentEditSummaries,
  resolveActiveIdeAgentMessage,
  shouldShowIdeAgentCenterPanel,
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

  it('shows the center panel while the agent is busy or review is ready', () => {
    expect(
      shouldShowIdeAgentCenterPanel({
        layoutMode: 'ide',
        agentStreamActive: true,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 0,
      }),
    ).toBe(true);

    expect(
      shouldShowIdeAgentCenterPanel({
        layoutMode: 'operator',
        agentStreamActive: true,
        composerAgentBusy: false,
        reviewReadyCount: 0,
        editedFileCount: 0,
      }),
    ).toBe(false);

    expect(
      shouldShowIdeAgentCenterPanel({
        layoutMode: 'ide',
        agentStreamActive: false,
        composerAgentBusy: false,
        reviewReadyCount: 1,
        editedFileCount: 2,
      }),
    ).toBe(true);
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
      showReview: true,
      showApplyAll: true,
      reviewLabel: 'Review 2 files',
      applyLabel: 'Apply all',
    });
  });
});
