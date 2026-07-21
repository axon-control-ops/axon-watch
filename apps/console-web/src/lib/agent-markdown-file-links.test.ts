import { describe, expect, it } from 'vitest';

import {
  expandAgentFileDirectoryLists,
  linkifyWorkspacePathsInMarkdown,
} from './agent-markdown-file-links';
import { renderAgentMessageMarkdown } from './agent-message-markdown';

describe('agent-markdown-file-links', () => {
  it('expands Files (in dir) bare filenames into full workspace paths', () => {
    const source = [
      'Files (in output/signs/):',
      '',
      '- young-eagles-parent-gate-sign.svg',
      '- young-eagles-parent-gate-sign.pdf',
      '- render_parent_gate_sign.py',
    ].join('\n');

    const expanded = expandAgentFileDirectoryLists(source);
    expect(expanded).toContain(
      '[young-eagles-parent-gate-sign.svg](output/signs/young-eagles-parent-gate-sign.svg)',
    );
    expect(expanded).toContain(
      '[young-eagles-parent-gate-sign.pdf](output/signs/young-eagles-parent-gate-sign.pdf)',
    );
    expect(expanded).toContain(
      '[render_parent_gate_sign.py](output/signs/render_parent_gate_sign.py)',
    );
  });

  it('linkifies relative workspace paths outside code fences', () => {
    const html = renderAgentMessageMarkdown(
      'Wrote output/signs/young-eagles-parent-gate-sign.svg and kept `src/app.ts` for later.',
    );
    expect(html).toContain('href="output/signs/young-eagles-parent-gate-sign.svg"');
    expect(html).toContain('href="src/app.ts"');
  });

  it('does not rewrite paths inside fenced code blocks', () => {
    const linked = linkifyWorkspacePathsInMarkdown(
      ['```', 'output/signs/young-eagles-parent-gate-sign.svg', '```'].join('\n'),
    );
    expect(linked).not.toContain('](output/signs/');
    expect(linked).toContain('output/signs/young-eagles-parent-gate-sign.svg');
  });

  it('leaves existing markdown links alone', () => {
    const linked = linkifyWorkspacePathsInMarkdown(
      'See [plan](docs/plan.md) and also docs/other.md for context.',
    );
    expect(linked).toContain('[plan](docs/plan.md)');
    expect(linked).toContain('[docs/other.md](docs/other.md)');
  });
});
