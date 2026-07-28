import { reportTheaterOpen } from './report-theater-state';

const AUTO_START_COOLDOWN_MS = 12 * 60 * 1000;

let lastAutoStartAt = 0;
let lastAutoStartKey = '';

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
}

/** Initial hydration establishes a baseline; only a changed briefing may auto-open theater. */
export function isReportTheaterAutoStartTransition(
  previousBriefKey: string | undefined,
  currentBriefKey: string,
  eligible: boolean,
): boolean {
  return previousBriefKey !== undefined && previousBriefKey !== currentBriefKey && eligible;
}

/**
 * Semi/Full autonomy: VAXON opens Command Theater without the operator typing REPORT.
 */
export function shouldAutoStartReportTheater(input: AutoStartStandupInput): boolean {
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
}
