export type SentrySignalIssue = {
  id: string;
  shortId: string;
  title: string;
  level: string;
  count: number;
  permalink: string;
  culprit: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

export function sentryIssuesFromSignalMeta(meta: unknown): SentrySignalIssue[] {
  const record = asRecord(meta);
  if (!record) {
    return [];
  }
  if (String(record.signal_family || '').trim() !== 'child_project_monitor') {
    return [];
  }
  const raw = record.sentry_issues;
  if (!Array.isArray(raw)) {
    return [];
  }

  const issues: SentrySignalIssue[] = [];
  for (const entry of raw) {
    const item = asRecord(entry);
    if (!item) {
      continue;
    }
    const id = String(item.id || '').trim();
    if (!id) {
      continue;
    }
    issues.push({
      id,
      shortId: String(item.short_id || item.shortId || '').trim(),
      title: String(item.title || 'unknown').trim() || 'unknown',
      level: String(item.level || '').trim(),
      count: Number(item.count || 0) || 0,
      permalink: String(item.permalink || '').trim(),
      culprit: String(item.culprit || '').trim(),
    });
  }
  return issues;
}
