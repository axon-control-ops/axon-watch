import { describe, expect, it } from 'vitest';

import {
  buildEditorBreadcrumbTrail,
  buildEditorPathSegments,
  formatEditorWorkspaceBreadcrumbLabel,
  parseMarkdownHeadingSymbols,
  resolveEditorBreadcrumbFilePath,
  resolveMarkdownSymbolAtLine,
} from './editor-breadcrumb-view';

describe('editor-breadcrumb-view', () => {
  it('splits file paths into workspace, folder, and file segments', () => {
    const segments = buildEditorPathSegments('workspace_smoke', 'apps/console-web/README.md');
    expect(segments.map((segment) => segment.label)).toEqual([
      'smoke',
      'apps',
      'console-web',
      'README.md',
    ]);
    expect(segments.at(-1)?.kind).toBe('file');
  });

  it('shortens workspace breadcrumb labels', () => {
    expect(formatEditorWorkspaceBreadcrumbLabel('workspace_axon_watch')).toBe('axon_watch');
    expect(formatEditorWorkspaceBreadcrumbLabel('workspace-smoke')).toBe('smoke');
  });

  it('uses the real workspace path for agent edit review drafts', () => {
    expect(
      resolveEditorBreadcrumbFilePath({
        source: 'draft',
        filePath: 'apps/console-web/src/lib/ide-agent-edit-review.test.ts',
        id: 'draft:agent-edit-review:apps-console-web-src-lib-ide-agent-edit-review.test.ts',
        title: 'ide-agent-edit-review.test.ts · review',
        value: '# Agent review · apps/console-web/src/lib/ide-agent-edit-review.test.ts\n',
        resourcePath:
          'agent-reports/agent-edit-review:apps-console-web-src-lib-ide-agent-edit-review.test.ts.md',
      }),
    ).toBe('apps/console-web/src/lib/ide-agent-edit-review.test.ts');
  });

  it('parses markdown headings for symbol breadcrumbs', () => {
    const content = ['# Intro', 'text', '## Setup', 'more'].join('\n');
    expect(parseMarkdownHeadingSymbols(content)).toEqual([
      { line: 1, level: 1, text: 'Intro' },
      { line: 3, level: 2, text: 'Setup' },
    ]);
    expect(resolveMarkdownSymbolAtLine(content, 4)?.text).toBe('Setup');
  });

  it('appends the active markdown symbol to the breadcrumb trail', () => {
    const content = ['# Product', '', '## Editor', 'body'].join('\n');
    const trail = buildEditorBreadcrumbTrail({
      workspaceId: 'workspace_smoke',
      filePath: 'README.md',
      content,
      cursorLine: 4,
      language: 'markdown',
    });

    expect(trail.at(-1)).toMatchObject({
      kind: 'symbol',
      label: 'Editor',
      revealLine: 3,
    });
  });
});
