import { reportTheaterOpen } from './report-theater-state';

const AUTO_START_COOLDOWN_MS = 12 * 60 * 1000;
const AUTO_START_PENDING_MS = 20_000;

/** Operator policy: Command Theater opens only via REPORT / STAND-UP — never from briefing polls. */
export const REPORT_THEATER_AUTO_START_ENABLED = false;

let lastAutoStartAt = 0;
let lastAutoStartKey = '';
let autoStartPendingUntil = 0;

export type AutoStartStandupInput = {
  autonomyMode: string | null | undefined;
  privacyMode: boolean;
  spokenAlertsEnabled: boolean;
  pendingApprovals: number;
  topSignalCount: number;
  awaitingEngagementCount: number;
  degradedActive: boolean;
  /** Stable briefing fingerprint / advise hash to avoid repeat stand-ups. */
  briefKey: string;
  now?: number;
};

export function resetReportTheaterAutoStartForTests(): void {
  lastAutoStartAt = 0;
  lastAutoStartKey = '';
  autoStartPendingUntil = 0;
}

/** True while Full/Semi just kicked off REPORT — skip passive advisory speech. */
export function isReportTheaterAutoStartPending(now = Date.now()): boolean {
  return reportTheaterOpen.value || now < autoStartPendingUntil;
}

/** Initial hydration establishes a quiet baseline; only a changed briefing may auto-open theater. */
export function isReportTheaterAutoStartTransition(
  previousBriefKey: string | undefined,
  currentBriefKey: string,
  eligible: boolean,
): boolean {
  return previousBriefKey !== undefined && previousBriefKey !== currentBriefKey && eligible;
}

/**
 * Stand-up is operator-initiated. Autonomy still speaks advisories and can
 * execute after an explicit REPORT — it must not open Command Theater alone.
 */
export function shouldStartReportTheaterForBriefing(input: {
  autonomyMode: string | null | undefined;
  previousBriefKey: string | undefined;
  currentBriefKey: string;
  eligible: boolean;
}): boolean {
  if (!REPORT_THEATER_AUTO_START_ENABLED) {
    return false;
  }
  if (!input.eligible) {
    return false;
  }
  const mode = String(input.autonomyMode || 'manual').trim().toLowerCase();
  if (mode === 'full') {
    return true;
  }
  return isReportTheaterAutoStartTransition(
    input.previousBriefKey,
    input.currentBriefKey,
    true,
  );
}

/**
 * Semi/Full autonomy used to open Command Theater without REPORT.
 * Disabled by policy — keep the helper for tests / future opt-in flag.
 */
export function shouldAutoStartReportTheater(input: AutoStartStandupInput): boolean {
  if (!REPORT_THEATER_AUTO_START_ENABLED) {
    return false;
  }
  if (reportTheaterOpen.value) {
    return false;
  }
  if (input.privacyMode || !input.spokenAlertsEnabled) {
    return false;
  }
  const mode = String(input.autonomyMode || 'manual').trim().toLowerCase();
  if (mode !== 'semi' && mode !== 'full') {
    return false;
  }
  const actionable =
    input.pendingApprovals > 0 ||
    input.topSignalCount > 0 ||
    input.awaitingEngagementCount > 0 ||
    input.degradedActive;
  if (!actionable) {
    return false;
  }
  const now = input.now ?? Date.now();
  const key = input.briefKey.trim() || 'default';
  if (key === lastAutoStartKey && now - lastAutoStartAt < AUTO_START_COOLDOWN_MS) {
    return false;
  }
  if (now - lastAutoStartAt < 45_000) {
    // Hard floor so briefing polls cannot stack stand-ups.
    return false;
  }
  return true;
}

export function markReportTheaterAutoStarted(briefKey: string, now = Date.now()): void {
  lastAutoStartAt = now;
  lastAutoStartKey = briefKey.trim() || 'default';
  autoStartPendingUntil = now + AUTO_START_PENDING_MS;
}
