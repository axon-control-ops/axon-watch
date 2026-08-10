import { describe, expect, it } from 'vitest';

import {
  buildCodexUsageStatusChip,
  buildStatusBarCodexUsageZone,
  codexUsageSummaryLine,
} from './codex-usage-view';

describe('codex-usage-view', () => {
  it('summarizes local Codex activity without pretending it is account quota', () => {
    const chip = buildCodexUsageStatusChip({
      ok: true,
      events_24h: 12,
      estimated_bytes_24h: 1536,
      message: 'Local telemetry only.',
    });
    expect(chip?.label).toBe('CODEX 1.5kB log');
    expect(chip?.title).toContain('not a live account-quota percentage');
    expect(codexUsageSummaryLine({ ok: true, events_24h: 12, estimated_bytes_24h: 1536 }))
      .toContain('12 local log events');
  });

  it('surfaces observed usage limits as warning status-bar chips', () => {
    const zone = buildStatusBarCodexUsageZone({
      ok: true,
      limit_reached: true,
      limit_reset_hint: 'Resets around 01:00 UTC.',
    });
    expect(zone?.label).toBe('CODEX LIMIT');
    expect(zone?.tone).toBe('warning');
    expect(zone?.title).toContain('01:00 UTC');
  });

  it('keeps unavailable telemetry muted', () => {
    const zone = buildStatusBarCodexUsageZone({
      ok: false,
      message: 'Codex local usage telemetry unavailable on this host.',
    });
    expect(zone?.label).toBe('CODEX ?');
    expect(zone?.tone).toBe('default');
  });
});
