/**
 * Plain-English delivery / handoff lines for the Team dock.
 * Raw pipeline fields (worker branches, PR URLs, CI tokens) stay on hover.
 */

const URL_RE = /https?:\/\/[^\s)`'"]+/gi;
const WORKER_BRANCH_RE = /\bworker\/run_[a-z0-9]+\b/gi;
const RUN_ID_RE = /\brun_[a-z0-9]{6,}\b/gi;
const PR_NUMBER_RE = /\/pull\/(\d+)\b/i;

const STAGE_PHRASES: Record<string, string> = {
  ci_green: 'CI checks passed',
  ci_passed: 'CI checks passed',
  ci_success: 'CI checks passed',
  ci_pending: 'CI checks are still running',
  ci_failed: 'CI checks failed',
  ci_failure: 'CI checks failed',
  ci_red: 'CI checks failed',
  draft_pr: 'a draft pull request is ready',
  draft_ready: 'a draft pull request is ready',
  pr_open: 'a draft pull request is open',
  published: 'the update was published',
  shipping: 'shipping is in progress',
  blocked: 'delivery is blocked',
  waiting: 'delivery is waiting',
  no_change: 'no delivery change needed',
};

function normalizeToken(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');
}

function extractUrl(text: string): string | null {
  const match = text.match(URL_RE);
  return match?.[0]?.trim() || null;
}

function extractPrNumber(url: string): string | null {
  const match = url.match(PR_NUMBER_RE);
  return match?.[1] || null;
}

function stripTechnicalTokens(text: string): string {
  return text
    .replace(URL_RE, ' ')
    .replace(WORKER_BRANCH_RE, ' ')
    .replace(RUN_ID_RE, ' ')
    .replace(/`+/g, ' ')
    .replace(/\b(success|failure|cancelled|neutral|skipped)\b/gi, ' ')
    .replace(/[·|]+/g, ' ')
    .replace(/\s*[-–—]\s*/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function stagePhrase(stage: string): string | null {
  const key = normalizeToken(stage);
  if (!key) {
    return null;
  }
  if (STAGE_PHRASES[key]) {
    return STAGE_PHRASES[key];
  }
  if (key.includes('ci') && (key.includes('green') || key.includes('pass'))) {
    return 'CI checks passed';
  }
  if (key.includes('ci') && key.includes('fail')) {
    return 'CI checks failed';
  }
  if (key.includes('draft') || key.includes('pr')) {
    return 'a draft pull request is ready';
  }
  const words = key.replace(/_/g, ' ').trim();
  return words ? words : null;
}

function ciPhrase(ciStatus: string): string | null {
  const key = normalizeToken(ciStatus);
  if (!key) {
    return null;
  }
  if (key === 'success' || key === 'passed' || key === 'green') {
    return 'CI checks passed';
  }
  if (key === 'failure' || key === 'failed' || key === 'red') {
    return 'CI checks failed';
  }
  if (key === 'pending' || key === 'queued' || key === 'in_progress') {
    return 'CI checks are still running';
  }
  return null;
}

/**
 * Build a short operator-facing handoff sentence from delivery fields.
 * Returns null when there is nothing useful to say.
 */
export function humanizeEmployeeDeliveryHandoff(input: {
  stage?: string | null;
  detail?: string | null;
  draftPrUrl?: string | null;
  ciStatus?: string | null;
}): string | null {
  const stage = String(input.stage || '').trim();
  const detail = String(input.detail || '').trim();
  const draftPrUrl =
    String(input.draftPrUrl || '').trim() || extractUrl(detail) || '';
  const ciStatus = String(input.ciStatus || '').trim();

  if (!stage && !detail && !draftPrUrl && !ciStatus) {
    return null;
  }

  const fromCi = ciPhrase(ciStatus);
  const fromStage = stagePhrase(stage);
  const stageKey = normalizeToken(stage);
  const running =
    Boolean(fromCi?.includes('still running')) ||
    stageKey === 'ci_pending' ||
    stageKey.includes('pending');

  if (draftPrUrl && running) {
    const prNumber = extractPrNumber(draftPrUrl);
    return prNumber
      ? `Latest handoff: Checks are still running on draft pull request #${prNumber}.`
      : 'Latest handoff: Checks are still running on the open draft pull request.';
  }

  const parts: string[] = [];
  if (fromCi) {
    parts.push(fromCi);
  } else if (fromStage && !fromStage.startsWith('a draft')) {
    parts.push(fromStage);
  }

  if (draftPrUrl) {
    const prNumber = extractPrNumber(draftPrUrl);
    parts.push(
      prNumber
        ? `draft pull request #${prNumber} is ready`
        : 'a draft pull request is ready',
    );
  } else if (fromStage?.startsWith('a draft') && !parts.includes(fromStage)) {
    parts.push(fromStage);
  }

  if (!parts.length) {
    const cleaned = stripTechnicalTokens(detail || stage);
    if (!cleaned) {
      return 'Latest handoff is ready to review.';
    }
    // Avoid dumping leftover machine tokens as the whole line.
    if (/^[a-z0-9_./:-]+$/i.test(cleaned) && cleaned.length < 28) {
      return `Latest handoff: ${cleaned.replace(/_/g, ' ')}.`;
    }
    if (cleaned.length > 120) {
      return `Latest handoff: ${cleaned.slice(0, 119).trim()}…`;
    }
    return `Latest handoff: ${cleaned}.`;
  }

  // Deduplicate near-identical CI phrases.
  const unique = [...new Set(parts)];
  if (unique.length === 1) {
    return `Latest handoff: ${unique[0]}.`;
  }
  const last = unique[unique.length - 1];
  const head = unique.slice(0, -1).join(', ');
  return `Latest handoff: ${head}, and ${last}.`;
}

export type EmployeeDeliveryLinks = {
  draftPrUrl: string | null;
  ciRunUrl: string | null;
  prNumber: string | null;
  running: boolean;
};

function prChecksUrl(prUrl: string): string | null {
  const cleaned = prUrl.replace(/[?#].*$/, '').replace(/\/+$/, '');
  if (!/\/pull\/\d+$/i.test(cleaned)) {
    return null;
  }
  return `${cleaned}/checks`;
}

/** Clickable PR / CI targets for the Team dock while delivery is in flight. */
export function resolveEmployeeDeliveryLinks(input: {
  stage?: string | null;
  detail?: string | null;
  draftPrUrl?: string | null;
  ciRunUrl?: string | null;
  ciStatus?: string | null;
}): EmployeeDeliveryLinks | null {
  const detail = String(input.detail || '').trim();
  const draftPrUrl =
    String(input.draftPrUrl || '').trim() || extractUrl(detail) || null;
  const explicitCi = String(input.ciRunUrl || '').trim() || null;
  // When the Actions run URL is not yet persisted, the PR checks tab is still watchable.
  const ciRunUrl = explicitCi || (draftPrUrl ? prChecksUrl(draftPrUrl) : null);
  if (!draftPrUrl && !ciRunUrl) {
    return null;
  }
  const stageKey = normalizeToken(String(input.stage || ''));
  const ciKey = normalizeToken(String(input.ciStatus || ''));
  const running =
    stageKey === 'ci_pending' ||
    stageKey.includes('pending') ||
    ciKey === 'pending' ||
    ciKey === 'queued' ||
    ciKey === 'in_progress';
  return {
    draftPrUrl,
    ciRunUrl,
    prNumber: draftPrUrl ? extractPrNumber(draftPrUrl) : null,
    running,
  };
}

/** Raw delivery detail for hover / screen-reader expansion. */
export function employeeDeliveryDetailTooltip(input: {
  stage?: string | null;
  detail?: string | null;
  draftPrUrl?: string | null;
  ciStatus?: string | null;
}): string | null {
  const bits = [
    input.stage?.trim(),
    input.detail?.trim(),
    input.draftPrUrl?.trim(),
    input.ciStatus?.trim(),
  ].filter(Boolean);
  if (!bits.length) {
    return null;
  }
  return bits.join(' · ');
}
