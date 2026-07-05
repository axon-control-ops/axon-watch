import type { RunRecord } from '../contracts/canonical';

const LEGACY_SUMMARY_LABELS: Record<string, string> = {
  health: 'Health check',
  'api/health': 'Health check',
  'runtime/summary': 'Health check',
  'git status': 'Git status',
  ls: 'List workspace files',
  'list files': 'List workspace files',
  dir: 'List workspace files',
  'resume from review': 'Resume from review',
  'resume review': 'Resume from review',
  'resume-from-review': 'Resume from review',
};

export function formatRunShortId(runId: string): string {
  const core = runId.startsWith('run_') ? runId.slice(4) : runId;
  return core.slice(0, 6);
}

export function humanizeRunSummary(summary: string): string {
  const trimmed = summary.trim();
  if (!trimmed) {
    return 'Operator task';
  }

  const lowered = trimmed.toLowerCase();
  const legacy = LEGACY_SUMMARY_LABELS[lowered];
  if (legacy) {
    return legacy;
  }

  const readMatch = /^(?:read|cat)\s+(.+)$/i.exec(trimmed);
  if (readMatch) {
    return `Read ${readMatch[1].trim()}`;
  }

  if (lowered.includes('readme') && !lowered.startsWith('read ')) {
    return 'Read README.md';
  }

  return trimmed;
}

export function formatRunDisplayName(
  run: Pick<RunRecord, 'summary' | 'detail' | 'run_id'>,
): string {
  return humanizeRunSummary(run.summary);
}

export function formatRunIdentityLabel(
  run: Pick<RunRecord, 'summary' | 'detail' | 'run_id'>,
): string {
  return `${formatRunDisplayName(run)} · #${formatRunShortId(run.run_id)}`;
}

export function formatRunCommandDetail(run: Pick<RunRecord, 'summary' | 'detail'>): string | null {
  const detail = run.detail?.trim();
  if (detail && detail.toLowerCase().startsWith('operator command:')) {
    return detail.slice('operator command:'.length).trim();
  }

  const summary = run.summary?.trim();
  if (summary && summary !== humanizeRunSummary(summary)) {
    return summary;
  }

  return null;
}
