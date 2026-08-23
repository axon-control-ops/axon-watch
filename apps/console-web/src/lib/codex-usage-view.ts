import type { CodexUsageSnapshot } from '../api/runtime-api';

export type CodexUsageChip = {
  label: string;
  tone: 'ready' | 'warn' | 'muted';
  title: string;
  ariaLabel: string;
};

function formatBytes(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  const n = Number(value);
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}MB`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}kB`;
  }
  return `${n}B`;
}

export function codexUsageSummaryLine(usage: CodexUsageSnapshot | null | undefined): string {
  if (usage?.limit_reached) {
    return usage.limit_reset_hint?.trim() || 'Codex usage limit reached.';
  }
  if (!usage?.ok) {
    return usage?.message?.trim() || 'Codex local usage telemetry unavailable on this host.';
  }
  const events = usage.events_24h ?? null;
  const bytes = formatBytes(usage.estimated_bytes_24h);
  if (events != null) {
    return `${events} local log events in 24h · ${bytes} estimated log volume`;
  }
  return usage.message?.trim() || 'Codex usage loaded';
}

export function buildCodexUsageStatusChip(
  usage: CodexUsageSnapshot | null | undefined,
): CodexUsageChip | null {
  if (!usage) {
    return null;
  }
  if (usage.limit_reached) {
    return {
      label: 'CODEX LIMIT',
      tone: 'warn',
      title: codexUsageSummaryLine(usage),
      ariaLabel: `Codex usage limit reached. ${codexUsageSummaryLine(usage)}`,
    };
  }
  if (!usage.ok) {
    return {
      label: 'CODEX ?',
      tone: 'muted',
      title: codexUsageSummaryLine(usage),
      ariaLabel: `Codex usage unavailable. ${codexUsageSummaryLine(usage)}`,
    };
  }
  return {
    label: `CODEX ${formatBytes(usage.estimated_bytes_24h)} log`,
    tone: 'ready',
    title: `${codexUsageSummaryLine(usage)}. This is local activity telemetry, not a live account-quota percentage.`,
    ariaLabel: `Codex usage. ${codexUsageSummaryLine(usage)}`,
  };
}

export const CODEX_USAGE_STATUS_BAR_CHIP_ID = 'codex-usage';

export function buildStatusBarCodexUsageZone(
  usage: CodexUsageSnapshot | null | undefined,
): {
  id: typeof CODEX_USAGE_STATUS_BAR_CHIP_ID;
  label: string;
  tone: 'default' | 'success' | 'warning';
  title: string;
  ariaLabel: string;
} | null {
  const chip = buildCodexUsageStatusChip(usage);
  if (!chip) {
    return null;
  }
  return {
    id: CODEX_USAGE_STATUS_BAR_CHIP_ID,
    label: chip.label,
    tone: chip.tone === 'warn' ? 'warning' : chip.tone === 'ready' ? 'success' : 'default',
    title: chip.title,
    ariaLabel: chip.ariaLabel,
  };
}
