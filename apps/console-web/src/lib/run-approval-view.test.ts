import { describe, expect, it } from 'vitest';

import { describeApprovalBanner } from './run-approval-view';

describe('approval banner reason', () => {
  it('surfaces the actual question for an ask-blocked run', () => {
    const view = describeApprovalBanner(
      "Blocked on operator decision: How should I unblock Priya's commit + draft PR?",
    );
    expect(view.isAskBlock).toBe(true);
    expect(view.question).toBe("How should I unblock Priya's commit + draft PR?");
    expect(view.bannerCopy).toContain("How should I unblock Priya's commit + draft PR?");
  });

  it('warns that Reject cancels the whole task on an ask-block', () => {
    const view = describeApprovalBanner('Blocked on operator decision: pick a scope');
    expect(view.rejectLabel).toBe('Cancel this task');
    expect(view.rejectWarning).toContain('whole task');
  });

  it('labels Approve honestly as resuming without an answer', () => {
    const view = describeApprovalBanner('Blocked on operator decision: pick a scope');
    expect(view.approveLabel).toBe('Resume without answering');
  });

  it('falls back to the generic tool-consent copy for a real Cursor pause', () => {
    const view = describeApprovalBanner('Awaiting Full Access approval');
    expect(view.isAskBlock).toBe(false);
    expect(view.bannerCopy).toContain('Full Access is paused');
    expect(view.approveLabel).toBe('Approve');
    expect(view.rejectLabel).toBe('Reject');
  });

  it('falls back to the generic copy when current_step is empty', () => {
    const view = describeApprovalBanner(null);
    expect(view.isAskBlock).toBe(false);
  });
});
