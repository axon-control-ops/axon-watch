import { describe, expect, it } from 'vitest';

import {
  buildCursorUsageBars,
  buildCursorUsageStatusChip,
  buildStatusBarUsageZone,
  cursorUsageSummaryLine,
} from './cursor-usage-view';

describe('cursor-usage-view', () => {
  it('builds Cursor-like pool bars from live usage', () => {
    const bars = buildCursorUsageBars({
      ok: true,
      auto_percent_used: 86.9,
      api_percent_used: 100,
      total_percent_used: 89.5,
      on_demand_enabled: true,
      membership_type: 'pro',
    });
    expect(bars.map((bar) => [bar.id, bar.percent])).toEqual([
      ['total', 90],
      ['auto', 87],
      ['api', 100],
    ]);
    expect(cursorUsageSummaryLine({
      ok: true,
      auto_percent_used: 86.9,
      api_percent_used: 100,
      total_percent_used: 89.5,
      on_demand_enabled: true,
      membership_type: 'pro',
    })).toContain('Total 90%');
    const chip = buildCursorUsageStatusChip({
      ok: true,
      auto_percent_used: 86.9,
      api_percent_used: 100,
      total_percent_used: 89.5,
      on_demand_enabled: true,
    });
    expect(chip?.label).toMatch(/USAGE 90%/);
    expect(chip?.label).toMatch(/AUTO 87%/);
    expect(chip?.label).toMatch(/API 100%/);
    // API at 100% is warn regardless of total.
    expect(chip?.tone).toBe('warn');
  });

  it('maps usage into the console footer zone with Auto and API', () => {
    const zone = buildStatusBarUsageZone({
      ok: true,
      auto_percent_used: 86.9,
      api_percent_used: 72,
      total_percent_used: 89.5,
    });
    expect(zone?.id).toBe('cursor-usage');
    expect(zone?.label).toBe('USAGE 90% · AUTO 87% · API 72%');
    expect(zone?.tone).toBe('success');
  });

  it('marks near-exhausted pools as warn', () => {
    const chip = buildCursorUsageStatusChip({
      ok: true,
      auto_percent_used: 99,
      api_percent_used: 100,
      total_percent_used: 99,
    });
    expect(chip?.tone).toBe('warn');
  });
});
