import type { ClaudeUsageSnapshot } from '../api/runtime-api';

export type ClaudeUsageStat = {
  id: 'recent' | 'week' | 'sessions' | 'cost';
  label: string;
  value: string;
  hint: string;
};

export type ClaudeUsageChip = {
  label: string;
  tone: 'ready' | 'warn' | 'muted';
  title: string;
  ariaLabel: string;
};

function formatTokens(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  const n = Number(value);
  if (n >= 1_000_000) {
    return `${(n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1)}M`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}k`;
  }
  return `${n}`;
}

function formatUsd(value: number | null | undefined): string {
  if (value == null || Number.isNaN(Number(value))) {
    return '—';
  }
  return `$${Number(value).toFixed(2)}`;
}

/**
 * Anthropic has no personal "current period usage" API the way Cursor's
 * dashboard does, so there is no real percent-of-plan figure to show here.
 * These stats are real local Claude Code telemetry (tokens/sessions/messages
 * from the CLI's own stats-cache) plus a live "usage limit reached" flag
 * observed from actual run failures — not a fabricated quota bar.
 */
export function buildClaudeUsageStats(usage: ClaudeUsageSnapshot | null | undefined): ClaudeUsageStat[] {
  const recent = usage?.most_recent_day;
  return [
    {
      id: 'recent',
      label: recent ? `Logged ${recent.date}` : 'Most recent day',
      value: formatTokens(recent?.tokens),
      hint: recent
        ? `${recent.messages} messages · ${recent.sessions} session${recent.sessions === 1 ? '' : 's'}`
        : 'No local Claude Code telemetry logged yet.',
    },
    {
      id: 'week',
      label: 'Last 7 logged days',
      value: formatTokens(usage?.tokens_7d),
      hint: 'Tokens across all models, summed from local Claude Code stats.',
    },
    {
      id: 'sessions',
      label: 'All-time sessions',
      value: usage?.total_sessions == null ? '—' : `${usage.total_sessions}`,
      hint: usage?.total_messages == null ? '' : `${usage.total_messages} messages total`,
    },
    {
      id: 'cost',
      label: 'Lifetime API-equivalent',
      value: formatUsd(usage?.lifetime_estimated_cost_usd),
      hint: 'Estimate only — subscription plans are not metered per token; verify real spend in the Anthropic Console.',
    },
  ];
}

export function claudeUsageSummaryLine(usage: ClaudeUsageSnapshot | null | undefined): string {
  if (usage?.limit_reached) {
    return usage.limit_reset_hint?.trim() || 'Claude usage limit reached.';
  }
  if (!usage?.ok) {
    return usage?.message?.trim() || 'Claude usage telemetry unavailable on this host.';
  }
  const recent = usage.most_recent_day;
  if (recent) {
    return `Logged ${recent.date}: ${formatTokens(recent.tokens)} tokens · ${recent.messages} messages`;
  }
  return usage.message?.trim() || 'Usage loaded';
}

export function buildClaudeUsageStatusChip(
  usage: ClaudeUsageSnapshot | null | undefined,
): ClaudeUsageChip | null {
  if (!usage) {
    return null;
  }
  if (usage.limit_reached) {
    return {
      label: 'CLAUDE LIMIT',
      tone: 'warn',
      title: claudeUsageSummaryLine(usage),
      ariaLabel: `Claude usage limit reached. ${claudeUsageSummaryLine(usage)}`,
    };
  }
  if (!usage.ok) {
    return {
      label: 'CLAUDE ?',
      tone: 'muted',
      title: claudeUsageSummaryLine(usage),
      ariaLabel: `Claude usage unavailable. ${claudeUsageSummaryLine(usage)}`,
    };
  }
  const recentTokens = usage.most_recent_day?.tokens;
  // Suffix "tok" explicitly — Cursor's chip next to this one reads in percent
  // ("USAGE 90%"), so a bare "CLAUDE 81k" reads as a percentage by association.
  const label = recentTokens == null ? 'CLAUDE OK' : `CLAUDE ${formatTokens(recentTokens)} tok`;
  const title = claudeUsageSummaryLine(usage);
  return {
    label,
    tone: 'ready',
    title,
    ariaLabel: `Claude usage. ${title}`,
  };
}

export const CLAUDE_USAGE_STATUS_BAR_CHIP_ID = 'claude-usage';

export function isClaudeUsageStatusBarChip(id: string): boolean {
  return id === CLAUDE_USAGE_STATUS_BAR_CHIP_ID;
}

/** Map Claude usage into the persistent console footer status-bar zone shape. */
export function buildStatusBarClaudeUsageZone(
  usage: ClaudeUsageSnapshot | null | undefined,
): {
  id: typeof CLAUDE_USAGE_STATUS_BAR_CHIP_ID;
  label: string;
  tone: 'default' | 'success' | 'warning';
  title: string;
  ariaLabel: string;
} | null {
  const chip = buildClaudeUsageStatusChip(usage);
  if (!chip) {
    return null;
  }
  return {
    id: CLAUDE_USAGE_STATUS_BAR_CHIP_ID,
    label: chip.label,
    tone: chip.tone === 'warn' ? 'warning' : chip.tone === 'ready' ? 'success' : 'default',
    title: chip.title,
    ariaLabel: chip.ariaLabel,
  };
}
