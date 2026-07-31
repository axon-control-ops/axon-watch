import { describe, expect, it } from 'vitest';

import { normalizeAgentProseMarkdown, renderAgentMessageMarkdown } from './agent-message-markdown';
import { parseLeadStandupReport } from './lead-standup-card';

describe('normalizeAgentProseMarkdown', () => {
  it('repairs bold glued into a GFM table header', () => {
    const raw =
      "**Here’s where things stand*| Step | Push to parent? | Push to staff? |\n|------|-----------------|----------------|\n| Ask to confirm tier | Yes | No |";
    const fixed = normalizeAgentProseMarkdown(raw);
    expect(fixed).toContain("**Here’s where things stand**");
    expect(fixed).toContain('\n\n| Step | Push to parent? | Push to staff? |');
    const html = renderAgentMessageMarkdown(raw);
    expect(html).toContain('<table>');
    expect(html).toContain('<th>Step</th>');
    expect(html).not.toContain('stand*|');
  });

  it('converts unicode bullets to GFM lists', () => {
    const html = renderAgentMessageMarkdown('• Confirm — yes.\n• Join group — no.');
    expect(html).toContain('<ul>');
    expect(html).toContain('<li>Confirm — yes.</li>');
  });
});

describe('parseLeadStandupReport', () => {
  it('parses a Lead stand-up with confidence and verification notice', () => {
    const text = [
      'Sir King — here is how parent push works.',
      '',
      "**Here’s where things stand*| Step | Push to parent? |",
      '|------|-----------------|',
      '| Ask to confirm | Yes |',
      '',
      '**Open risk:** tokens.',
      '',
      'Confidence: 9/10',
      '---',
      '**Verification notice:** this reply contains claims that could not be fully verified:',
      '- reply claims file changes but no edit receipts were recorded',
    ].join('\n');

    const card = parseLeadStandupReport(normalizeAgentProseMarkdown(text), {
      leadName: 'Imani',
    });
    expect(card).not.toBeNull();
    expect(card?.leadName).toBe('Imani');
    expect(card?.confidence).toBe('9/10');
    expect(card?.intro).toContain('parent push works');
    expect(card?.bodyMarkdown).toMatch(/where things stand/i);
    expect(card?.verificationNotice).toMatch(/edit receipts/i);
  });
});
