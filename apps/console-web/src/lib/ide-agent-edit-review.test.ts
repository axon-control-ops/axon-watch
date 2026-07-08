import { describe, expect, it } from 'vitest';

import {
  agentEditReviewDocumentId,
  agentEditReviewDocumentTitle,
  formatAgentEditReviewContent,
  shouldOpenWorkspaceFileForEditReview,
} from './ide-agent-edit-review';

describe('ide-agent-edit-review', () => {
  it('builds stable review document ids from workspace paths', () => {
    expect(agentEditReviewDocumentId('apps/console-web/src/lib/foo.ts')).toBe(
      'draft:agent-edit-review:apps-console-web-src-lib-foo.ts',
    );
  });

  it('formats review buffer content from transcript diffs', () => {
    const content = formatAgentEditReviewContent({
      path: 'README.md',
      added: 1,
      removed: 0,
      diff: '--- a/README.md\n+++ b/README.md\n+<!-- hi -->',
      open: false,
    });

    expect(content).toContain('# Agent review · README.md');
    expect(content).toContain('+<!-- hi -->');
  });

  it('notes streaming edits without diff lines', () => {
    const content = formatAgentEditReviewContent({
      path: 'src/app.ts',
      added: 0,
      removed: 0,
      diff: '',
      open: true,
    });

    expect(content).toContain('still streaming');
    expect(content).toContain('(No diff captured yet.)');
  });

  it('titles review tabs from file basename', () => {
    expect(agentEditReviewDocumentTitle('apps/console-web/src/IdeAgentReviewStrip.vue')).toBe(
      'IdeAgentReviewStrip.vue · review',
    );
  });

  it('falls back to workspace files when no diff is captured yet', () => {
    expect(
      shouldOpenWorkspaceFileForEditReview({
        diff: '',
        open: false,
      }),
    ).toBe(true);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        diff: '',
        open: true,
      }),
    ).toBe(false);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        diff: '--- a/README.md\n+++ b/README.md\n+line',
        open: false,
      }),
    ).toBe(false);
  });
});
