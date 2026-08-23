import { describe, expect, it } from 'vitest';

import {
  agentMessageLooksLikeMarkdown,
  isInterimAgentStatus,
  extractReadMarkdownFilePath,
  isMarkdownFileAgentResponse,
  renderAgentMessageMarkdown,
  shouldAutoOpenAgentReportInEditor,
  shouldOfferMarkdownPreview,
  shouldOfferOpenInEditor,
  shouldRenderAgentProseMarkdown,
  shouldUseAgentMarkdownBlock,
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

  it('wraps markdown tables for Cursor-style scrolling', () => {
    const html = renderAgentMessageMarkdown('| Slot | Behavior |\n| --- | --- |\n| Top | Yes |');
    expect(html).toContain('markdown-table-wrap');
    expect(html).toContain('<table>');
    expect(html).toContain('<th>Slot</th>');
  });

  it('promotes empty-header key/value tables so credentials render as HTML tables', () => {
    const content = [
      'Login details for Lesego',
      '',
      '| |',
      '|---|---|',
      '| Username | lesego.mkhwebane |',
      '| Initial password | Lesego2026! |',
      '| Staff ID | s007 |',
    ].join('\n');
    const html = renderAgentMessageMarkdown(content);
    expect(html).toContain('<table>');
    expect(html).toContain('<th>Field</th>');
    expect(html).toContain('<th>Value</th>');
    expect(html).toContain('<td>Username</td>');
    expect(html).toContain('<td>lesego.mkhwebane</td>');
    expect(html).not.toContain('|---|---|');
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

  it('renders all non-empty agent prose blocks', () => {
    expect(shouldUseAgentMarkdownBlock('')).toBe(false);
    expect(shouldUseAgentMarkdownBlock('Search returned no results — trying Cursor docs.', false)).toBe(
      false,
    );
    expect(shouldUseAgentMarkdownBlock('## Summary\n\n- item one')).toBe(true);
    expect(shouldUseAgentMarkdownBlock('Plain prose without markdown syntax still formats.')).toBe(
      true,
    );
  });

  it('shows markdown file reads as thread links instead of inline preview', () => {
    const content = [
      'Executed `read_file` (ok) for run run_abc.',
      '',
      '```',
      '# README.md',
      '',
      '**Axon-X** is the product.',
      '```',
    ].join('\n');
    expect(shouldUseAgentMarkdownBlock(content)).toBe(false);
    expect(isMarkdownFileAgentResponse(content)).toBe(true);
  });

  it('keeps interim status lines out of markdown preview while streaming', () => {
    expect(shouldUseAgentMarkdownBlock('Searching the docs…', false)).toBe(false);
  });

  it('renders complete agent prose as markdown even without list markers', () => {
    expect(
      shouldRenderAgentProseMarkdown('Confidence: 7/10\n\nDelivery is blocked until CI is green.', {
        isComplete: true,
      }),
    ).toBe(true);
  });

  it('does not treat multi-line prose as interim status', () => {
    expect(isInterimAgentStatus('Done.\n\nMore details follow.')).toBe(false);
    expect(isInterimAgentStatus('**Summary**\n\n- item one')).toBe(false);
  });

  it('detects markdown file read responses for workspace editor open', () => {
    const content = [
      'Executed `read_file` (ok) for run run_abc.',
      '',
      '```',
      '# README.md',
      '',
      '**Axon-X** is the product.',
      '```',
    ].join('\n');
    expect(isMarkdownFileAgentResponse(content)).toBe(true);
    expect(extractReadMarkdownFilePath(content)).toBe('README.md');
    expect(shouldAutoOpenAgentReportInEditor(content)).toBe(false);
  });

  it('keeps agent report markdown in the chat lane', () => {
    const report = ['# Cursor vs EduDash Pro', '', '## Images', '', '| Method | How |', '| --- | --- |'].join(
      '\n',
    );
    expect(shouldOfferOpenInEditor(report, true)).toBe(true);
    const longReport = `${report}\n\n${'Additional findings about image upload.\n'.repeat(20)}`;
    expect(shouldAutoOpenAgentReportInEditor(longReport)).toBe(false);
    expect(shouldAutoOpenAgentReportInEditor('# Short report\n\nOne paragraph.')).toBe(false);
  });

  it('does not auto-open block-structured agent transcripts in the editor', () => {
    const content = [
      ':::research Web search',
      '- Example | https://example.com/',
      'Snippet text',
      ':::',
      '',
      '# Final report',
      '',
      'This should stay in the lane.',
    ].join('\n');
    expect(shouldAutoOpenAgentReportInEditor(content)).toBe(false);
  });
});
