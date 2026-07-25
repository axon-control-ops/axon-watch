import { describe, expect, it } from 'vitest';

import {
  agentEditReviewDocumentId,
  agentEditReviewDocumentTitle,
  extractProposedFileContentFromDiff,
  formatAgentEditReviewContent,
  isAgentEditReviewDocumentId,
  isMarkdownAgentEditPath,
  shouldOpenWorkspaceFileForEditReview,
  truncateDiffLinesForDock,
  truncateMarkdownForDockPreview,
} from './ide-agent-edit-review';

describe('ide-agent-edit-review', () => {
  it('builds stable review document ids from workspace paths', () => {
    expect(agentEditReviewDocumentId('apps/console-web/src/lib/foo.ts')).toBe(
      'draft:agent-edit-review:apps-console-web-src-lib-foo.ts',
    );
    expect(isAgentEditReviewDocumentId('draft:agent-edit-review:apps-console-web-src-lib-foo.ts')).toBe(
      true,
    );
    expect(isAgentEditReviewDocumentId('draft:agent-other')).toBe(false);
  });

  it('detects markdown review paths', () => {
    expect(isMarkdownAgentEditPath('docs/plan.md')).toBe(true);
    expect(isMarkdownAgentEditPath('src/app.ts')).toBe(false);
  });

  it('strips unified-diff markers for proposed markdown bodies', () => {
    const proposed = extractProposedFileContentFromDiff(
      [
        '--- /dev/null',
        '+++ b/docs/plan.md',
        '@@ -0,0 +1,4 @@',
        '+# Plan',
        '+',
        '+Hello **world**',
        '+',
      ].join('\n'),
    );

    expect(proposed).toBe('# Plan\n\nHello **world**\n');
    expect(proposed).not.toContain('+#');
  });

  it('formats non-markdown review buffers as diffs', () => {
    const content = formatAgentEditReviewContent({
      path: 'src/app.ts',
      added: 1,
      removed: 0,
      diff: '--- a/src/app.ts\n+++ b/src/app.ts\n+const x = 1;',
      open: false,
    });

    expect(content).toContain('# Agent review · src/app.ts');
    expect(content).toContain('+const x = 1;');
  });

  it('formats markdown review buffers as readable markdown (no + prefixes)', () => {
    const content = formatAgentEditReviewContent({
      path: 'docs/EduDashPro.documentation/DASHBOARD_UI_UX_UPGRADE_PLAN.md',
      added: 4,
      removed: 0,
      diff: [
        '--- /dev/null',
        '+++ b/docs/EduDashPro.documentation/DASHBOARD_UI_UX_UPGRADE_PLAN.md',
        '@@ -0,0 +1,4 @@',
        '+# Parent & Principal Dashboard UI/UX Upgrade Plan',
        '+',
        '+## 1. Competitive benchmark',
        '+',
      ].join('\n'),
      open: false,
    });

    expect(content).toContain('# Parent & Principal Dashboard UI/UX Upgrade Plan');
    expect(content).toContain('## 1. Competitive benchmark');
    expect(content).not.toContain('+# Parent');
    expect(content).not.toContain('# Agent review ·');
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

  it('opens workspace files for completed edits (Cursor-style), including SVG canvas paths', () => {
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'src/app.ts',
        diff: '',
        open: false,
      }),
    ).toBe(true);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'src/app.ts',
        diff: '',
        open: true,
      }),
    ).toBe(false);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'README.md',
        diff: '--- a/README.md\n+++ b/README.md\n+line',
        open: false,
      }),
    ).toBe(true);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'src/app.ts',
        diff: '--- a/src/app.ts\n+++ b/src/app.ts\n+line',
        open: false,
      }),
    ).toBe(true);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'output/signs/young-eagles-parent-gate-sign.svg',
        diff: '--- /dev/null\n+++ b/output/signs/young-eagles-parent-gate-sign.svg\n+<svg/>',
        open: false,
      }),
    ).toBe(true);
    expect(
      shouldOpenWorkspaceFileForEditReview({
        path: 'output/signs/young-eagles-parent-gate-sign.svg',
        diff: '+streaming',
        open: true,
      }),
    ).toBe(false);
  });

  it('truncates long markdown dock previews without cutting mid-word when possible', () => {
    const long = `${'# Title\n\n'}${'paragraph text. '.repeat(120)}`;
    const result = truncateMarkdownForDockPreview(long, 200);
    expect(result.truncated).toBe(true);
    expect(result.preview.endsWith('…')).toBe(true);
    expect(result.preview.length).toBeLessThan(long.length);
  });

  it('limits raw diff lines in the dock', () => {
    const diff = Array.from({ length: 50 }, (_, i) => `+line ${i}`).join('\n');
    const result = truncateDiffLinesForDock(diff, 10);
    expect(result.truncated).toBe(true);
    expect(result.lines).toHaveLength(11);
    expect(result.lines[10]).toContain('more lines');
  });
});
