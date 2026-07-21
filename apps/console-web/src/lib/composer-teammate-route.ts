/**
 * Deterministic soft-routing: wrong-teammate composer submits → owning role.
 * Keywords + owns overlap only — no model call.
 */

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { isBuildPlanImplementPrompt } from './build-plan-prompt';

export type TeammateRouteEmployee = Pick<
  CompanyEmployeeRecord,
  'employee_id' | 'name' | 'role' | 'role_label' | 'owns'
>;

export type TeammateRouteDecision = {
  shouldRoute: boolean;
  reason: string;
  employee?: TeammateRouteEmployee;
  fromEmployeeId?: string;
  fromName?: string;
  winnerScore?: number;
  secondScore?: number;
};

const MIN_WINNER_SCORE = 2;
const MIN_MARGIN = 2;

type RoleBag = {
  role: string;
  patterns: RegExp[];
  weight: number;
};

/** Specialist bags — lead is only used when triage language dominates. */
const ROLE_BAGS: RoleBag[] = [
  {
    role: 'frontend',
    weight: 1,
    patterns: [
      /\bui\b/i,
      /\bux\b/i,
      /\bscreen\b/i,
      /\bcomponent\b/i,
      /\blayout\b/i,
      /\bexpo\b/i,
      /\bandroid\b/i,
      /\bapp-?config\b/i,
      /\bconfirmation\b/i,
      /\benrol+ment\b/i,
      /\bpopup\b/i,
      /\bmodal\b/i,
      /\btoast\b/i,
      /\bcard\b/i,
      /\btsx\b/i,
      /\bcss\b/i,
      /\bvue\b/i,
      /\bparent[- ]facing\b/i,
      /\bcanary build\b/i,
      /\bmissing (?:on|in) (?:the )?(?:app|ui|screen|build)\b/i,
    ],
  },
  {
    // Extra weight so UI confirmation work beats OTA/release vocabulary.
    role: 'frontend',
    weight: 2,
    patterns: [/\bconfirmation\b/i, /\benrol+ment\b/i, /\bpopup\b/i, /\bmodal\b/i],
  },
  {
    role: 'backend',
    weight: 1,
    patterns: [
      /\bapi\b/i,
      /\bendpoint\b/i,
      /\b\/api\//i,
      /\bservice\b/i,
      /\bquality[- ]gate\b/i,
      /\bsupabase\b/i,
      /\brpc\b/i,
      /\bmigration\b/i,
      /\bschema\b/i,
      /\bpostgres\b/i,
      /\bserver\b/i,
    ],
  },
  {
    role: 'integrations',
    weight: 1,
    patterns: [
      /\bgithub actions\b/i,
      /\bworkflow\b/i,
      /\bsecrets?\b/i,
      /\brunner\b/i,
      /\bsdk\b/i,
      /\bconnector\b/i,
      /\beas\b/i,
      /\bota\b/i,
      /\bexpo-cli\b/i,
    ],
  },
  {
    role: 'watcher',
    weight: 1,
    patterns: [
      /\bsentry\b/i,
      /\bsignal\b/i,
      /\bhealth\b/i,
      /\bred[- ]build\b/i,
      /\balert\b/i,
      /\bposthog\b/i,
    ],
  },
  {
    role: 'lead',
    weight: 1,
    patterns: [
      /\bpriorit(?:y|ies)\b/i,
      /\btriage\b/i,
      /\bproduct direction\b/i,
      /\bwho should own\b/i,
      /\bhand[- ]?off\b/i,
    ],
  },
];

const PATH_ROLE_HINTS: Array<{ role: string; pattern: RegExp; weight: number }> = [
  { role: 'frontend', pattern: /\b(?:app|components|screens|styles)\/[\w./-]+\.(?:tsx?|jsx?|vue|css)\b/i, weight: 2 },
  { role: 'backend', pattern: /\b(?:services|api|server|supabase)\/[\w./-]+\.(?:ts|py|sql)\b/i, weight: 2 },
  { role: 'integrations', pattern: /\b\.github\/workflows\/[\w./-]+\.ya?ml\b/i, weight: 2 },
];

function normalizeRole(role: string): string {
  const cleaned = String(role || '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');
  if (cleaned === 'ui' || cleaned === 'ux' || cleaned === 'front_end') {
    return 'frontend';
  }
  if (cleaned === 'back_end') {
    return 'backend';
  }
  return cleaned;
}

function ownsOverlapScore(text: string, owns: string): number {
  const tokens = String(owns || '')
    .toLowerCase()
    .split(/[^a-z0-9+]+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 4);
  if (!tokens.length) {
    return 0;
  }
  const lower = text.toLowerCase();
  let hits = 0;
  for (const token of tokens) {
    if (lower.includes(token)) {
      hits += 1;
    }
  }
  return Math.min(hits, 3);
}

function scoreRole(text: string, role: string, owns: string): number {
  const normalized = normalizeRole(role);
  let score = 0;
  for (const bag of ROLE_BAGS) {
    if (bag.role !== normalized) {
      continue;
    }
    for (const pattern of bag.patterns) {
      if (pattern.test(text)) {
        score += bag.weight;
      }
    }
  }
  for (const hint of PATH_ROLE_HINTS) {
    if (hint.role === normalized && hint.pattern.test(text)) {
      score += hint.weight;
    }
  }
  score += ownsOverlapScore(text, owns);
  return score;
}

/**
 * Soft-route when the active teammate is clearly the wrong specialist for this prompt.
 * Requires an active employee thread; ambiguous prompts stay put.
 */
export function shouldSoftRouteToTeammate(
  promptText: string,
  currentEmployee: TeammateRouteEmployee | null | undefined,
  roster: readonly TeammateRouteEmployee[] | null | undefined,
): TeammateRouteDecision {
  if (!currentEmployee?.employee_id?.trim()) {
    return { shouldRoute: false, reason: 'no_active_employee' };
  }
  const employees = (roster ?? []).filter((row) => row.employee_id?.trim());
  if (employees.length < 2) {
    return { shouldRoute: false, reason: 'roster_too_small' };
  }

  const text = String(promptText || '').trim();
  if (!text) {
    return { shouldRoute: false, reason: 'empty_prompt' };
  }
  if (isBuildPlanImplementPrompt(text)) {
    return { shouldRoute: false, reason: 'build_plan_implement' };
  }

  const scored = employees.map((employee) => ({
    employee,
    score: scoreRole(text, employee.role, employee.owns),
  }));
  scored.sort((left, right) => right.score - left.score || left.employee.name.localeCompare(right.employee.name));

  const winner = scored[0];
  const second = scored[1];
  if (!winner) {
    return { shouldRoute: false, reason: 'no_match' };
  }

  const winnerScore = winner.score;
  const secondScore = second?.score ?? 0;
  if (winnerScore < MIN_WINNER_SCORE) {
    return { shouldRoute: false, reason: 'score_too_low', winnerScore, secondScore };
  }
  if (winnerScore - secondScore < MIN_MARGIN) {
    return { shouldRoute: false, reason: 'margin_too_low', winnerScore, secondScore };
  }

  const currentId = currentEmployee.employee_id.trim();
  if (winner.employee.employee_id.trim() === currentId) {
    return {
      shouldRoute: false,
      reason: 'already_owning',
      employee: winner.employee,
      winnerScore,
      secondScore,
    };
  }

  // Prefer routing only when current role loses clearly to winner role.
  const currentScore =
    scored.find((row) => row.employee.employee_id.trim() === currentId)?.score ?? 0;
  if (winnerScore - currentScore < MIN_MARGIN) {
    return {
      shouldRoute: false,
      reason: 'current_still_competitive',
      winnerScore,
      secondScore: currentScore,
    };
  }

  return {
    shouldRoute: true,
    reason: `role_${normalizeRole(winner.employee.role)}`,
    employee: winner.employee,
    fromEmployeeId: currentId,
    fromName: currentEmployee.name.trim() || 'teammate',
    winnerScore,
    secondScore,
  };
}
