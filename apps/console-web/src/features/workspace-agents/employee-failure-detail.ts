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
  /^Lane B (?:agent fallback reply generated|plan fallback failed)\s*\(([\s\S]*?)\s*\)?\s*$/i;
const DISPATCH_FAILURE_PREFIX = 'continuous worker dispatch failed:';

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
  /auth probe timed out/i,
  /auth probe failed/i,
  /cursor auth probe/i,
  /codex auth probe/i,
];

const FAILURE_NOISE_RE = /^(?:running as unit|invocation id|scope)[:\s]/i;

function pickPrimaryFailureCause(inner: string): string {
  const parts = inner
    .split(';')
    .map((part) => part.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .filter((part) => !FAILURE_NOISE_RE.test(part));
  if (!parts.length) {
    return inner.trim();
  }
  const rank = (part: string): number => {
    if (/ActionRequiredError|out of usage|increase limits/i.test(part)) {
      return 0;
    }
    if (RUNTIME_AUTH_MARKERS.some((marker) => marker.test(part))) {
      return 1;
    }
    if (/failed on\b/i.test(part)) {
      return 2;
    }
    if (/unavailable/i.test(part)) {
      return 4;
    }
    return 3;
  };
  return [...parts].sort((left, right) => rank(left) - rank(right))[0] ?? parts[0] ?? inner;
}

/** True when outcome detail is a success receipt, not a failure root cause. */
export function looksLikeSuccessfulOutcomeDetail(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  if (
    normalized === 'run completed' ||
    normalized === 'completed' ||
    normalized === 'success' ||
    normalized === 'succeeded'
  ) {
    return true;
  }
  return (
    normalized.startsWith('run completed') ||
    /^completed\b/.test(normalized) ||
    /\bsucceeded\b/.test(normalized)
  );
}

/** Worker shift blocked because implementation was requested but no workspace files changed. */
export function isCompletionGateFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return (
    normalized.includes('completion gate') ||
    normalized.includes('no changed files') ||
    normalized.includes('produced no changed files')
  );
}

/** Gate 6 acceptance / verification evidence did not pass. */
export function isGate6AcceptanceFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return (
    normalized.includes('gate 6') ||
    normalized.includes('acceptance_evidence') ||
    normalized.includes('acceptance evidence') ||
    normalized.includes('lane b finalization failed')
  );
}

/** Strip Lane B fallback wrappers so dock and retry drafts show the root cause. */
export function normalizeOperatorFailureDetail(detail: string | null | undefined): string {
  const cleaned = (detail ?? '').replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return cleaned;
  }
  if (cleaned.toLowerCase().startsWith(DISPATCH_FAILURE_PREFIX)) {
    const tail = cleaned.slice(DISPATCH_FAILURE_PREFIX.length).trim();
    return pickPrimaryFailureCause(tail || cleaned);
  }
  const match = cleaned.match(LANE_B_FALLBACK_NORMALIZE_RE);
  if (match) {
    return pickPrimaryFailureCause((match[1] ?? '').replace(/\s+/g, ' ').trim());
  }
  return pickPrimaryFailureCause(cleaned);
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

/** Matches Cursor usage-limit blocks before a shift could start or finish.
 *
 * Bare ActionRequiredError is not enough — require an explicit usage phrase.
 */
export function isUsageLimitFailure(detail: string | null | undefined): boolean {
  const hay = `${detail ?? ''} ${normalizeOperatorFailureDetail(detail)}`;
  return (
    /out of usage/i.test(hay) ||
    /increase limits/i.test(hay) ||
    /hit your usage/i.test(hay) ||
    /usage limit/i.test(hay) ||
    /used 100% of your included/i.test(hay)
  );
}

/** True when the agent runtime could not authenticate (CLI login, vault keys, or auth probe). */
export function isRuntimeAuthFailure(detail: string | null | undefined): boolean {
  const hay = `${detail ?? ''} ${normalizeOperatorFailureDetail(detail)}`;
  return RUNTIME_AUTH_MARKERS.some((marker) => marker.test(hay));
}

/**
 * Delivery was blocked by a working-as-intended policy gate (e.g. private-document
 * paths never leave a workspace automatically) rather than a transient failure.
 * Retrying re-runs the same task against the same working tree and fails the same
 * way every time — an operator must remove/relocate the file first.
 */
export function isNonRetriableWorkspaceBlockFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return (
    normalized.includes('private_company_material:') ||
    normalized.includes('working-as-intended behavior, not an error to retry')
  );
}

/** Auth-probe timeout vs missing login — both are runtime auth, different operator next step. */
export function isRuntimeAuthProbeFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return (
    normalized.includes('auth probe timed out') ||
    normalized.includes('auth probe failed') ||
    normalized.includes('cursor auth probe') ||
    normalized.includes('codex auth probe')
  );
}

/** Formatting miss on the mandatory Critical Review Confidence line. */
export function isMissingConfidenceFailure(detail: string | null | undefined): boolean {
  const normalized = normalizeOperatorFailureDetail(detail).toLowerCase();
  if (!normalized) {
    return false;
  }
  return (
    normalized.includes('critical review clause missing') ||
    normalized.includes('must end with confidence')
  );
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
  if (isUsageLimitFailure(firstClause)) {
    return 'usage limits blocked the agent runtime';
  }
  if (/unavailable/i.test(firstClause)) {
    return 'no agent runtime was ready';
  }
  if (isRuntimeAuthFailure(firstClause)) {
    if (
      /auth probe timed out/i.test(firstClause) ||
      /auth probe failed/i.test(firstClause)
    ) {
      return 'Cursor CLI auth timed out';
    }
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
