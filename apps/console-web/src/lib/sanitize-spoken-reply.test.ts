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

  it('keeps clock times with a colon', () => {
    const spoken = sanitizeSpokenReply('Briefing ready at 12:30.');
    expect(spoken).toContain('12:30');
  });

  it('leaves concise template replies unchanged', () => {
    const line = '2 approvals on the board — Attention has the detail.';
    expect(sanitizeSpokenReply(line)).toBe(line);
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
});
