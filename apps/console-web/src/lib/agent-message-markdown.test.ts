import { describe, expect, it } from 'vitest';

import {
  agentMessageLooksLikeMarkdown,
  renderAgentMessageMarkdown,
  shouldOfferMarkdownPreview,
  splitAgentMessageForPreview,
} from './agent-message-markdown';

describe('agent-message-markdown', () => {
  it('detects common markdown patterns', () => {
    expect(agentMessageLooksLikeMarkdown('## Summary\n\n- item one')).toBe(true);
    expect(agentMessageLooksLikeMarkdown('plain sentence only')).toBe(false);
  });

  it('renders markdown to html', () => {
    const html = renderAgentMessageMarkdown('**Health** check complete.');
    expect(html).toContain('<strong>Health</strong>');
  });

  it('extracts read_file fenced markdown from agent execution wrapper', () => {
    const content = [
      'Executed `read_file` (ok) for run run_abc.',
      '',
      '```',
      '# README.md',
      '',
      '**Axon-X** is the product.',
      '',
      '- item one',
      '```',
      '',
      'Phase is now review_ready. Review when ready.',
    ].join('\n');

    const parts = splitAgentMessageForPreview(content);
    expect(parts.executionIntent).toBe('read_file');
    expect(parts.hasMarkdownPreview).toBe(true);
    expect(parts.markdownSource).toContain('# README.md');
    expect(parts.preamble).toContain('Executed `read_file`');
    expect(parts.postamble).toContain('Phase is now review_ready');

    const html = renderAgentMessageMarkdown(content);
    expect(html).toContain('<strong>Axon-X</strong>');
    expect(html).toContain('<li>item one</li>');
  });

  it('offers preview for wrapped read_file output', () => {
    const content = 'Executed `read_file` (ok) for run x.\n\n```\n# Title\n```\n\nDone.';
    expect(shouldOfferMarkdownPreview(content)).toBe(true);
  });

  it('does not offer preview for git status fenced output', () => {
    const content = 'Executed `git_status` (ok) for run x.\n\n```\n## main\n M file.py\n```\n\nDone.';
    expect(shouldOfferMarkdownPreview(content)).toBe(false);
  });
});
