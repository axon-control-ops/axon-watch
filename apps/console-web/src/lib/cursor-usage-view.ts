import type { CursorUsageSnapshot } from '../api/runtime-api';

export type CursorUsageBar = {
  id: 'total' | 'auto' | 'api';
  label: string;
  percent: number | null;
  hint: string;
};

export type CursorUsageChip = {
  label: string;
  tone: 'ready' | 'warn' | 'muted';
  title: string;
  ariaLabel: string;
};

function roundPct(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(Number(value))) {
    return null;
  }
  return Math.max(0, Math.min(100, Math.round(Number(value))));
}

export function buildCursorUsageBars(usage: CursorUsageSnapshot | null | undefined): CursorUsageBar[] {
  return [
    {
      id: 'total',
      label: 'Total',
      percent: roundPct(usage?.total_percent_used),
      hint: usage?.display_message?.trim() || 'Combined included usage this billing cycle.',
    },
    {
      id: 'auto',
      label: 'Auto + Composer',
      percent: roundPct(usage?.auto_percent_used),
      hint:
        usage?.auto_display_message?.trim() ||
        'Additional Auto+Composer usage may consume API quota or on-demand spend.',
    },
    {
      id: 'api',
      label: 'API',
      percent: roundPct(usage?.api_percent_used),
      hint:
        usage?.api_display_message?.trim() ||
        'Additional API usage beyond included limits consumes on-demand spend.',
    },
  ];
}

export function cursorUsageSummaryLine(usage: CursorUsageSnapshot | null | undefined): string {
  if (!usage?.ok) {
    return usage?.message?.trim() || 'Usage unavailable — open Cursor Settings → Usage.';
  }
  const total = roundPct(usage.total_percent_used);
  const auto = roundPct(usage.auto_percent_used);
  const api = roundPct(usage.api_percent_used);
  const parts: string[] = [];
  if (total != null) {
    parts.push(`Total ${total}%`);
  }
  if (auto != null) {
    parts.push(`Auto ${auto}%`);
  }
  if (api != null) {
    parts.push(`API ${api}%`);
  }
  const membership = (usage.membership_type || '').trim();
  const onDemand =
    usage.on_demand_enabled === true
      ? 'on-demand on'
      : usage.on_demand_enabled === false
        ? 'on-demand off'
        : null;
  const meta = [membership, onDemand].filter(Boolean).join(' · ');
  if (!parts.length) {
    return meta || 'Usage loaded';
  }
  return meta ? `${parts.join(' · ')} · ${meta}` : parts.join(' · ');
}

export function buildCursorUsageStatusChip(
  usage: CursorUsageSnapshot | null | undefined,
): CursorUsageChip | null {
  if (!usage) {
    return null;
  }
  const total = roundPct(usage.total_percent_used);
  const auto = roundPct(usage.auto_percent_used);
  const api = roundPct(usage.api_percent_used);
  if (!usage.ok || total == null) {
    return {
      label: 'USAGE ?',
      tone: 'muted',
      title: cursorUsageSummaryLine(usage),
      ariaLabel: `Cursor usage unavailable. ${cursorUsageSummaryLine(usage)}`,
    };
  }
  const tone: CursorUsageChip['tone'] =
    total >= 95 || (auto != null && auto >= 98) || (api != null && api >= 98)
      ? 'warn'
      : 'ready';
  const parts = [`USAGE ${total}%`];
  if (auto != null) {
    parts.push(`AUTO ${auto}%`);
  }
  if (api != null) {
    parts.push(`API ${api}%`);
  }
  const label = parts.join(' · ');
  const title = cursorUsageSummaryLine(usage);
  return {
    label,
    tone,
    title,
    ariaLabel: `Cursor usage. ${title}`,
  };
}

export const CURSOR_USAGE_STATUS_BAR_CHIP_ID = 'cursor-usage';

export function isCursorUsageStatusBarChip(id: string): boolean {
  return id === CURSOR_USAGE_STATUS_BAR_CHIP_ID;
}

/** Map Cursor usage into the persistent console footer status-bar zone shape. */
export function buildStatusBarUsageZone(
  usage: CursorUsageSnapshot | null | undefined,
): {
  id: typeof CURSOR_USAGE_STATUS_BAR_CHIP_ID;
  label: string;
  tone: 'default' | 'success' | 'warning';
  title: string;
  ariaLabel: string;
} | null {
  const chip = buildCursorUsageStatusChip(usage);
  if (!chip) {
    return null;
  }
  return {
    id: CURSOR_USAGE_STATUS_BAR_CHIP_ID,
    label: chip.label,
    tone: chip.tone === 'warn' ? 'warning' : chip.tone === 'ready' ? 'success' : 'default',
    title: chip.title,
    ariaLabel: chip.ariaLabel,
  };
}
