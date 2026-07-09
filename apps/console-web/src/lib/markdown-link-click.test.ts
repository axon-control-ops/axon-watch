import { describe, expect, it } from 'vitest';

import {
  resolveMarkdownLinkTarget,
  resolveRelativeWorkspacePath,
} from './markdown-link-click';

describe('markdown-link-click', () => {
  it('resolves workspace-relative markdown links', () => {
    expect(resolveMarkdownLinkTarget('docs/planning/EXECUTION_PLAN.md')).toEqual({
      kind: 'workspace',
      path: 'docs/planning/EXECUTION_PLAN.md',
    });
  });

  it('resolves links relative to the active markdown file', () => {
    expect(
      resolveMarkdownLinkTarget('../README.md', 'docs/planning/EXECUTION_PLAN.md'),
    ).toEqual({
      kind: 'workspace',
      path: 'docs/README.md',
    });
    expect(resolveMarkdownLinkTarget('KAIRO_VOICE_IMPROVEMENT_PLAN.md', 'docs/planning/EXECUTION_PLAN.md')).toEqual({
      kind: 'workspace',
      path: 'docs/planning/KAIRO_VOICE_IMPROVEMENT_PLAN.md',
    });
  });

  it('treats external links separately from workspace files', () => {
    expect(resolveMarkdownLinkTarget('https://example.com/docs')).toEqual({
      kind: 'external',
      url: 'https://example.com/docs',
    });
  });

  it('rejects unsafe workspace paths', () => {
    expect(resolveMarkdownLinkTarget('../../etc/passwd')).toEqual({ kind: 'skip' });
  });

  it('normalizes relative workspace path segments', () => {
    expect(resolveRelativeWorkspacePath('docs/planning/EXECUTION_PLAN.md', './KAIRO_VOICE_IMPROVEMENT_PLAN.md')).toBe(
      'docs/planning/KAIRO_VOICE_IMPROVEMENT_PLAN.md',
    );
  });
});
