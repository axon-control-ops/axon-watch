import type { CompanyEmployeeRecord } from '../../contracts/canonical';

const FAILURE_DETAIL_MAX = 120;
const SPEAK_DETAIL_MAX = 160;

export function truncateFailureDetail(detail: string, max = FAILURE_DETAIL_MAX): string {
  if (detail.length <= max) {
    return detail;
  }
  return `${detail.slice(0, max - 1)}…`;
}

const RESTART_INTERRUPT_MARKERS = [
  'run interrupted by control-plane restart',
  'run cancelled after control-plane restart',
  'run paused after control-plane restart',
  'continuous worker dispatch lost on control-plane restart',
  'continuous worker dispatch paused on control-plane restart',
  'continuous worker dispatch cancelled after control-plane restart',
];

/** Matches control-plane restart reconciliation summaries on orphaned runs. */
export function isRestartInterruptedFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return RESTART_INTERRUPT_MARKERS.some((marker) => normalized.includes(marker));
}

const AGENT_RUNTIME_FALLBACK_RE =
  /^Lane B (?:agent fallback reply generated|plan fallback failed)\s*\(/i;
const LANE_B_FALLBACK_NORMALIZE_RE =
  /^Lane B (?:agent fallback reply generated|plan fallback failed)\s*\((.*)\)\s*$/i;
const DISPATCH_FAILURE_PREFIX = 'continuous worker dispatch failed:';

/** Strip Lane B fallback wrappers so dock and retry drafts show the root cause. */
export function normalizeOperatorFailureDetail(detail: string | null | undefined): string {
  const cleaned = (detail ?? '').replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return cleaned;
  }
  const match = cleaned.match(LANE_B_FALLBACK_NORMALIZE_RE);
  if (match) {
    const inner = (match[1] ?? '').replace(/\s+/g, ' ').trim();
    const primary = (inner.split(';')[0] ?? inner).trim();
    return primary || inner;
  }
  if (cleaned.toLowerCase().startsWith(DISPATCH_FAILURE_PREFIX)) {
    const tail = cleaned.slice(DISPATCH_FAILURE_PREFIX.length).trim();
    return tail || cleaned;
  }
  return cleaned;
}

/** True when the operator stopped the CLI before the shift could finish. */
export function isOperatorStoppedFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail);
  if (!normalized) {
    return false;
  }
  const lowered = normalized.toLowerCase();
  return (
    lowered.includes('runtime execution stopped by operator') ||
    lowered.includes('stopped by operator before the cli finished')
  );
}

/** Matches SIGTERM (143) or SIGKILL/OOM (137 / -9) when the agent session was killed. */
export function isAgentSessionInterruptedFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail);
  if (!normalized) {
    return false;
  }
  return (
    /exited with status 143/i.test(normalized) ||
    /exited with status 137/i.test(normalized) ||
    /exited with status -?9\b/i.test(normalized) ||
    /\boom[- ]?kill/i.test(normalized) ||
    /\bkilled by.*oom\b/i.test(normalized)
  );
}

/** Restart, operator stop, or SIGTERM — retry should continue rather than treat as a hard failure. */
export function isShiftContinuationFailure(detail: string | null | undefined): boolean {
  return (
    isRestartInterruptedFailure(detail) ||
    isOperatorStoppedFailure(detail) ||
    isAgentSessionInterruptedFailure(detail)
  );
}

export function employeeResolvedFailureDetail(employee: CompanyEmployeeRecord): string {
  return normalizeOperatorFailureDetail(employee.last_outcome_detail);
}

/** Matches Cursor usage-limit blocks before a shift could start or finish. */
export function isUsageLimitFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail);
  if (!normalized) {
    return false;
  }
  return (
    /out of usage/i.test(normalized) ||
    /increase limits/i.test(normalized) ||
    /ActionRequiredError/i.test(normalized)
  );
}

const RUNTIME_AUTH_MARKERS = [
  /not signed in/i,
  /cursor agent login/i,
  /codex login/i,
  /unlock \/vault/i,
  /vault locked/i,
  /cursor rejected CURSOR_API_KEY/i,
  /authentication failed/i,
  /authentication required/i,
  /api_key_invalid/i,
];

/** True when the agent runtime could not authenticate (CLI login or vault keys). */
export function isRuntimeAuthFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail);
  if (!normalized) {
    return false;
  }
  return RUNTIME_AUTH_MARKERS.some((marker) => marker.test(normalized));
}

/** Matches Lane B runtime fallback receipts where no CLI/cloud agent could run the shift. */
export function isAgentRuntimeFallbackFailure(detail: string | null | undefined): boolean {
  const text = (detail ?? '').trim();
  if (!text) {
    return false;
  }
  if (AGENT_RUNTIME_FALLBACK_RE.test(text)) {
    return true;
  }
  return text.toLowerCase().includes('runtime unavailable');
}

export function agentRuntimeFallbackSpeakDetail(detail: string): string {
  const normalized = normalizeOperatorFailureDetail(detail);
  const reason = normalized || detail.trim();
  const firstClause = reason.split(';')[0]?.trim() ?? reason;
  if (isOperatorStoppedFailure(firstClause)) {
    return 'the shift was stopped before it could finish';
  }
  if (/exited with status 143/i.test(firstClause)) {
    return 'the agent session was interrupted before it could finish';
  }
  if (/unavailable/i.test(firstClause)) {
    return 'no agent runtime was ready';
  }
  if (/out of usage/i.test(firstClause)) {
    return 'usage limits blocked the agent runtime';
  }
  if (isRuntimeAuthFailure(firstClause)) {
    return 'runtime auth is not ready';
  }
  return truncateFailureDetail(firstClause, SPEAK_DETAIL_MAX);
}

export function failureSpeakDetail(employee: CompanyEmployeeRecord): string | null {
  const raw = (employee.last_outcome_detail ?? '').trim();
  const detail = employeeResolvedFailureDetail(employee);
  if (!detail) {
    return null;
  }
  if (isRestartInterruptedFailure(detail)) {
    return 'the server restarted and cut the shift short';
  }
  if (isAgentRuntimeFallbackFailure(raw)) {
    return agentRuntimeFallbackSpeakDetail(raw);
  }
  return truncateFailureDetail(detail, SPEAK_DETAIL_MAX);
}
