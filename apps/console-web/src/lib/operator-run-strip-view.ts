import type { RunRecord } from '../contracts/canonical';

import { formatRunDisplayName, humanizeRunSummary } from './run-display';

const AUTO_COMPLETE_SUMMARY_KEYS = new Set([
  'git status',
  'health',
  'api/health',
  'runtime/summary',
  'ls',
  'list files',
  'dir',
  'check-health',
  'check health',
]);

export type ReviewReadyStripGroup = {
  key: string;
  label: string;
  count: number;
  runIds: string[];
  autoComplete: boolean;
};

export type OperatorRunStripView = {
  showStrip: boolean;
  totalCount: number;
  groups: ReviewReadyStripGroup[];
  headline: string;
  detail: string;
  defaultExpanded: boolean;
  allAutoComplete: boolean;
  completeAllLabel: string;
};

export function isAutoCompleteRunSummary(summary: string): boolean {
  const trimmed = summary.trim();
  if (!trimmed) {
    return false;
  }

  const lowered = trimmed.toLowerCase();
  if (AUTO_COMPLETE_SUMMARY_KEYS.has(lowered)) {
    return true;
  }

  if (/^(?:read|cat)\s+.+/i.test(trimmed)) {
    return true;
  }

  if (/^(?:open|show)\s+(?:the\s+)?readme\b/i.test(lowered)) {
    return true;
  }

  return false;
}

export function buildReviewReadyStripGroups(runs: RunRecord[]): ReviewReadyStripGroup[] {
  const groups = new Map<string, ReviewReadyStripGroup>();

  for (const run of runs) {
    const label = formatRunDisplayName(run);
    const key = humanizeRunSummary(run.summary).trim().toLowerCase() || label.toLowerCase();
    const existing = groups.get(key);
    if (existing) {
      existing.count += 1;
      existing.runIds.push(run.run_id);
      continue;
    }

    groups.set(key, {
      key,
      label,
      count: 1,
      runIds: [run.run_id],
      autoComplete: isAutoCompleteRunSummary(run.summary),
    });
  }

  return [...groups.values()].sort((left, right) => {
    if (right.count !== left.count) {
      return right.count - left.count;
    }
    return left.label.localeCompare(right.label);
  });
}

export function buildOperatorRunStripView(input: {
  reviewReadyRuns: RunRecord[];
  expanded?: boolean;
}): OperatorRunStripView {
  const totalCount = input.reviewReadyRuns.length;
  const groups = buildReviewReadyStripGroups(input.reviewReadyRuns);
  const allAutoComplete =
    totalCount > 0 && groups.every((group) => group.autoComplete);
  const showStrip = totalCount > 0;

  if (!showStrip) {
    return {
      showStrip: false,
      totalCount: 0,
      groups: [],
      headline: '',
      detail: '',
      defaultExpanded: false,
      allAutoComplete: false,
      completeAllLabel: 'Complete all',
    };
  }

  const primaryGroup = groups[0];
  const defaultExpanded = !allAutoComplete && totalCount <= 3;
  const expanded = input.expanded ?? defaultExpanded;

  let headline: string;
  let detail: string;

  if (allAutoComplete && totalCount > 1) {
    if (groups.length === 1 && primaryGroup) {
      headline = `${totalCount}× ${primaryGroup.label} verification runs`;
    } else {
      headline = `${totalCount} one-shot verification runs`;
    }
    detail = expanded
      ? 'These read-only commands are done — complete all to clear Mission Control.'
      : 'Collapsed queue · expand for breakdown · Complete all to clear.';
  } else if (totalCount === 1 && primaryGroup) {
    headline = `${primaryGroup.label} ready for review`;
    detail = primaryGroup.autoComplete
      ? 'Read output in Command results, then complete the run.'
      : 'Review evidence, then resume or complete.';
  } else {
    headline = `${totalCount} runs waiting for review`;
    detail = expanded
      ? 'Review each run or complete all when evidence looks good.'
      : 'Run queue collapsed · expand to inspect individual tasks.';
  }

  return {
    showStrip,
    totalCount,
    groups,
    headline,
    detail,
    defaultExpanded,
    allAutoComplete,
    completeAllLabel:
      totalCount > 1 ? `Complete all (${totalCount})` : 'Complete run',
  };
}

export function shouldHideLiveExecutionFeed(input: {
  reviewReadyRuns: RunRecord[];
  primaryActiveRun: RunRecord | null;
}): boolean {
  if (!input.primaryActiveRun || input.primaryActiveRun.phase !== 'review_ready') {
    return false;
  }

  if (!isAutoCompleteRunSummary(input.primaryActiveRun.summary)) {
    return false;
  }

  return input.reviewReadyRuns.every((run) => isAutoCompleteRunSummary(run.summary));
}
