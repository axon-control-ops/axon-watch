import { describe, expect, it } from 'vitest';

import {
  formatAgentEditReviewContent,
  shouldOpenWorkspaceFileForEditReview,
} from './ide-agent-edit-review';

const base = {
  path: 'hooks/useParentProgressReports.ts',
  diff: '@@ -0,0 +1 @@\n+export const a = 1;',
  added: 1,
  removed: 0,
};

describe('sandbox review drafts', () => {
  it('keeps the draft so checkout-only files are not opened from the bound root', () => {
    // Opening the real path showed an empty editor for sandbox-created files.
    expect(
      shouldOpenWorkspaceFileForEditReview({ ...base, open: false, preferDraft: true }),
    ).toBe(false);
  });

  it('still opens the real file for ordinary finished edits', () => {
    expect(shouldOpenWorkspaceFileForEditReview({ ...base, open: false })).toBe(true);
  });

  it('renders the diff body in the draft', () => {
    const content = formatAgentEditReviewContent({ ...base, open: false, preferDraft: true });
    expect(content).toContain('+export const a = 1;');
    expect(content).toContain('+1  -0');
  });

  it('does not claim the agent is still streaming', () => {
    const content = formatAgentEditReviewContent({ ...base, open: false, preferDraft: true });
    expect(content).not.toContain('still streaming');
  });
});
