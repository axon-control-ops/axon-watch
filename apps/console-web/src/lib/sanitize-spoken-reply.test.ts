import { describe, expect, it } from 'vitest';

import {
  cleanAgentReplyText,
  formatConversationDisplayReply,
  sanitizeSpokenReply,
  splitSpokenReplyChunks,
} from './sanitize-spoken-reply';

const AGENT_DUMP = `:::thinking
Investigating the cause of the DashPro Workspace spike.
:::
Investigating what's driving the DashPro workspace spike — checking monitoring scripts and recent ops changes.

:::tool Glob

:::tool Read supabase/migrations/20260708120000_monitor_storage_bucket_usage.sql

From my side right now, DashPro is not spiking — no active runs, no top signal, systems nominal.

If you are seeing a spike in Axon, the repo points at Supabase storage, not the database. Recent ops work was added because storage is blowing the one-gigabyte free tier; the cleanup notes call out the \`tts-audio\` bucket at roughly four hundred twenty-seven megabytes as the main offender.

From my side right now, DashPro is not spiking — no active runs, no top signal, systems nominal.

If you are seeing a spike in Axon, the repo points at Supabase storage, not the database. Recent ops work was added because storage is blowing the one-gigabyte free tier; the cleanup notes call out the \`tts-audio\` bucket at roughly four hundred twenty-seven megabytes as the main offender.`;

describe('sanitizeSpokenReply', () => {
  it('removes stream blocks and tool calls from agent dumps', () => {
    const display = formatConversationDisplayReply(AGENT_DUMP);
    expect(display).not.toContain(':::tool');
    expect(display).not.toContain(':::thinking');
    expect(display).not.toContain('Glob');
    expect(display).not.toContain('supabase/migrations');
    expect(display).toContain('DashPro is not spiking');
    expect(display).toContain('Supabase storage');
  });

  it('keeps multiple readable paragraphs for display and speech', () => {
    const display = formatConversationDisplayReply(AGENT_DUMP);
    expect(display.split('\n\n').length).toBeGreaterThan(1);
    const spoken = sanitizeSpokenReply(AGENT_DUMP);
    expect(spoken).toContain('DashPro is not spiking');
    expect(spoken).toContain('Supabase storage');
    expect(spoken.length).toBeGreaterThan(420);
  });

  it('strips markdown punctuation that TTS reads literally', () => {
    const spoken = sanitizeSpokenReply('Use the `tts-audio` bucket and "Command" panel.');
    expect(spoken).not.toContain('`');
    expect(spoken).not.toContain('"');
    expect(spoken).toContain('tts-audio');
    expect(spoken).toContain('Command');
  });

  it('softens paths and symbols so TTS does not say slash or colon', () => {
    const spoken = sanitizeSpokenReply('Open apps/console-web/src/lib/foo.ts:42 🙂');
    expect(spoken).not.toContain('/');
    expect(spoken).not.toContain(':');
    expect(spoken).not.toContain('🙂');
    expect(spoken.toLowerCase()).toContain('apps');
    expect(spoken.toLowerCase()).toContain('console-web');
    expect(spoken).toContain('42');
  });

  it('speaks readiness scores as percent instead of one hundred one hundred', () => {
    const spoken = sanitizeSpokenReply(
      'Production readiness 100/100 (ready) — clear to operate with confidence',
    );
    expect(spoken.toLowerCase()).toContain('100 percent');
    expect(spoken).not.toMatch(/100\s+100/);
  });

  it('keeps clock times with a colon', () => {
    const spoken = sanitizeSpokenReply('Briefing ready at 12:30.');
    expect(spoken).toContain('12:30');
  });

  it('strips literal spoken symbol words', () => {
    const spoken = sanitizeSpokenReply(
      'Open apps slash console web colon forty two with a smiley face',
    );
    expect(spoken.toLowerCase()).not.toContain('slash');
    expect(spoken.toLowerCase()).not.toContain('colon');
    expect(spoken.toLowerCase()).not.toContain('smiley');
    expect(spoken.toLowerCase()).toContain('apps');
  });

  it('normalizes em-dashes in concise template replies for TTS pacing', () => {
    const line = '2 approvals on the board — Attention has the detail.';
    expect(sanitizeSpokenReply(line)).toBe(
      '2 approvals on the board, Attention has the detail.',
    );
  });

  it('splits long spoken replies into chunks', () => {
    const spoken = sanitizeSpokenReply(AGENT_DUMP);
    const chunks = splitSpokenReplyChunks(spoken, 220);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.join(' ')).toContain('DashPro is not spiking');
  });

  it('cleans agent reply text without truncating to one paragraph', () => {
    const cleaned = cleanAgentReplyText(AGENT_DUMP);
    expect(cleaned).toContain('DashPro is not spiking');
    expect(cleaned).toContain('Supabase storage');
    expect(cleaned).not.toContain(':::tool');
  });

  it('strips debug-reproduce blocks so numbered steps are not spoken', () => {
    const raw = [
      'I instrumented the speech path.',
      '',
      ':::debug-reproduce',
      '1. Keep Debug mode on.',
      '2. Listen for numbered steps.',
      ':::',
    ].join('\n');
    const cleaned = cleanAgentReplyText(raw);
    expect(cleaned).toContain('I instrumented the speech path.');
    expect(cleaned).not.toContain(':::debug-reproduce');
    expect(cleaned).not.toMatch(/^\s*1\.\s+/m);
    expect(cleaned).not.toContain('Listen for numbered steps');
    const spoken = sanitizeSpokenReply(raw);
    expect(spoken.toLowerCase()).not.toContain('listen for numbered steps');
    expect(spoken).toContain('instrumented');
  });

  it('strips reproduce steps separated by blank lines inside the block', () => {
    const raw = [
      'Ready for reproduction.',
      '',
      ':::debug-reproduce',
      '1. Keep Debug mode on.',
      '',
      '2. Listen for numbered steps.',
      ':::',
    ].join('\n');
    const cleaned = cleanAgentReplyText(raw);
    expect(cleaned).toContain('Ready for reproduction.');
    expect(cleaned).not.toMatch(/^\s*2\.\s+/m);
    expect(cleaned).not.toContain('Listen for numbered steps');
  });

  it('keeps digit+role phrases speakable (4 Lead → four, Lead-team)', () => {
    const spoken = sanitizeSpokenReply('4 Lead plans awaiting engagement in VAXON.');
    expect(spoken.toLowerCase()).toContain('four, lead-team');
    expect(spoken).not.toMatch(/\b4\s+Lead\b/);
    expect(spoken).toMatch(/Vekson/i);
    expect(spoken).not.toMatch(/\bVAXON\b/);
  });

  it('speaks VAXON as Vekson, never letter-by-letter', () => {
    expect(sanitizeSpokenReply('VAXON is watching.')).toMatch(/^Vekson is watching/i);
    expect(sanitizeSpokenReply('Engage in V.A.X.O.N now.')).toMatch(/Vekson/i);
    expect(sanitizeSpokenReply('Say V A X O N clearly.')).toMatch(/Vekson/i);
    expect(sanitizeSpokenReply('VAXON online.')).not.toMatch(/\bV\s+A\s+X\s+O\s+N\b/);
  });

  it('speaks Sipho as See-po', () => {
    expect(sanitizeSpokenReply('Sipho is speaking.')).toMatch(/See-po is speaking/i);
    expect(sanitizeSpokenReply('Ask Sipho for status.')).not.toMatch(/\bSipho\b/);
  });

  it('speaks Thabo as Ta-bo while display text remains canonical', () => {
    expect(formatConversationDisplayReply('Thabo is reporting.')).toBe('Thabo is reporting.');
    expect(sanitizeSpokenReply('Thabo is reporting.')).toMatch(/^Ta-bo is reporting/i);
  });

  it('keeps Lead-team hyphen and spells CI for TTS', () => {
    const spoken = sanitizeSpokenReply(
      'Four Lead-team plans waiting. DashPro CI failed on main.',
    );
    expect(spoken).toMatch(/four, Lead-team/i);
    expect(spoken).toMatch(/C I/);
    expect(spoken).not.toMatch(/\bCI\b/);
  });
});
