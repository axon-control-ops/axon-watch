import { describe, expect, it } from 'vitest';

import {
  buildClaudeUsageStats,
  buildClaudeUsageStatusChip,
  buildStatusBarClaudeUsageZone,
  claudeUsageSummaryLine,
} from './claude-usage-view';

describe('claude-usage-view', () => {
  it('builds stat rows from local Claude Code telemetry', () => {
    const stats = buildClaudeUsageStats({
      ok: true,
      most_recent_day: { date: '2026-04-30', tokens: 80951, messages: 144, sessions: 3 },
      tokens_7d: 142570,
      total_sessions: 106,
      total_messages: 22179,
      lifetime_estimated_cost_usd: 12.34,
    });
    expect(stats.map((stat) => stat.id)).toEqual(['recent', 'week', 'sessions', 'cost']);
    expect(stats[0].value).toBe('80.9k');
    expect(stats[1].value).toBe('142.6k');
    expect(stats[2].value).toBe('106');
    expect(stats[3].value).toBe('$12.34');
  });

  it('summarizes the most recent logged day when available', () => {
    const summary = claudeUsageSummaryLine({
      ok: true,
      most_recent_day: { date: '2026-04-30', tokens: 80951, messages: 144, sessions: 3 },
    });
    expect(summary).toContain('2026-04-30');
    expect(summary).toContain('144 messages');
  });

  it('flags a warn chip and reset hint when the usage limit is reached', () => {
    const usage = {
      ok: true,
      limit_reached: true,
      limit_reset_hint: 'Resets around 18:00 UTC.',
    };
    expect(claudeUsageSummaryLine(usage)).toBe('Resets around 18:00 UTC.');
    const chip = buildClaudeUsageStatusChip(usage);
    expect(chip?.label).toBe('CLAUDE LIMIT');
    expect(chip?.tone).toBe('warn');
    const zone = buildStatusBarClaudeUsageZone(usage);
    expect(zone?.id).toBe('claude-usage');
    expect(zone?.tone).toBe('warning');
  });

  it('marks unavailable telemetry as a muted chip', () => {
    const chip = buildClaudeUsageStatusChip({ ok: false, message: 'no stats-cache on host' });
    expect(chip?.tone).toBe('muted');
    expect(chip?.label).toBe('CLAUDE ?');
  });

  it('returns null chip/zone when usage is missing entirely', () => {
    expect(buildClaudeUsageStatusChip(null)).toBeNull();
    expect(buildStatusBarClaudeUsageZone(undefined)).toBeNull();
  });
});
