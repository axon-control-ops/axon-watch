/**
 * Deterministic soft-routing: wrong-teammate / cold-start → owning role.
 * Keywords + owns overlap only — model tie-break is a separate server step.
 */

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { isBuildPlanImplementPrompt } from './build-plan-prompt';

export type TeammateRouteEmployee = Pick<
  CompanyEmployeeRecord,
  'employee_id' | 'name' | 'role' | 'role_label' | 'owns'
>;

export type TeammateRouteSource = 'deterministic' | 'model';

export type TeammateRouteDecision = {
  shouldRoute: boolean;
  reason: string;
  employee?: TeammateRouteEmployee;
  fromEmployeeId?: string;
  fromName?: string;
  winnerScore?: number;
  secondScore?: number;
  source?: TeammateRouteSource;
  ambiguous?: boolean;
  routingReceipt?: string | null;
  modelReceipt?: Record<string, unknown> | null;
};

export const MIN_WINNER_SCORE = 2;
export const MIN_MARGIN = 2;

const AMBIGUOUS_REASONS = new Set([
  'margin_too_low',
  'current_still_competitive',
  'score_too_low',
]);

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
  {
    role: 'frontend',
    pattern: /\b(?:app|components|screens|styles)\/[\w./-]+\.(?:tsx?|jsx?|vue|css)\b/i,
    weight: 2,
  },
  {
    role: 'backend',
    pattern: /\b(?:services|api|server|supabase)\/[\w./-]+\.(?:ts|py|sql)\b/i,
    weight: 2,
  },
  {
    role: 'integrations',
    pattern: /\b\.github\/workflows\/[\w./-]+\.ya?ml\b/i,
    weight: 2,
  },
];

export function normalizeTeammateRole(role: string): string {
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

export function scoreTeammateRole(text: string, role: string, owns: string): number {
  const normalized = normalizeTeammateRole(role);
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

export function isAmbiguousTeammateRoute(decision: TeammateRouteDecision): boolean {
  if (decision.reason === 'score_too_low') {
    return Boolean(decision.ambiguous);
  }
  return Boolean(decision.ambiguous) || AMBIGUOUS_REASONS.has(decision.reason);
}

type ScoredEmployee = {
  employee: TeammateRouteEmployee;
  score: number;
};

function scoreRoster(
  text: string,
  employees: readonly TeammateRouteEmployee[],
): ScoredEmployee[] {
  const scored = employees.map((employee) => ({
    employee,
    score: scoreTeammateRole(text, employee.role, employee.owns),
  }));
  scored.sort(
    (left, right) =>
      right.score - left.score || left.employee.name.localeCompare(right.employee.name),
  );
  return scored;
}

/**
 * Soft-route when the prompt clearly belongs to another specialist.
 * Cold-start (no active employee) picks a clear roster winner.
 * Ambiguous prompts stay put and set `ambiguous` for optional model tie-break.
 */
export function shouldSoftRouteToTeammate(
  promptText: string,
  currentEmployee: TeammateRouteEmployee | null | undefined,
  roster: readonly TeammateRouteEmployee[] | null | undefined,
): TeammateRouteDecision {
  const employees = (roster ?? []).filter((row) => row.employee_id?.trim());
  if (employees.length < 2) {
    return { shouldRoute: false, reason: 'roster_too_small', source: 'deterministic' };
  }

  const text = String(promptText || '').trim();
  if (!text) {
    return { shouldRoute: false, reason: 'empty_prompt', source: 'deterministic' };
  }
  if (isBuildPlanImplementPrompt(text)) {
    return { shouldRoute: false, reason: 'build_plan_implement', source: 'deterministic' };
  }

  const scored = scoreRoster(text, employees);
  const winner = scored[0];
  const second = scored[1];
  if (!winner) {
    return { shouldRoute: false, reason: 'no_match', source: 'deterministic' };
  }

  const winnerScore = winner.score;
  const secondScore = second?.score ?? 0;
  const baseScores = {
    winnerScore,
    secondScore,
    source: 'deterministic' as const,
    employee: winner.employee,
  };

  if (winnerScore < MIN_WINNER_SCORE) {
    return {
      shouldRoute: false,
      reason: 'score_too_low',
      ...baseScores,
      ambiguous: winnerScore > 0,
    };
  }
  if (winnerScore - secondScore < MIN_MARGIN) {
    return {
      shouldRoute: false,
      reason: 'margin_too_low',
      ...baseScores,
      ambiguous: true,
    };
  }

  const currentId = currentEmployee?.employee_id?.trim() ?? '';
  if (!currentId) {
    return {
      shouldRoute: true,
      reason: `role_${normalizeTeammateRole(winner.employee.role)}`,
      employee: winner.employee,
      fromName: 'workspace',
      winnerScore,
      secondScore,
      source: 'deterministic',
    };
  }

  if (winner.employee.employee_id.trim() === currentId) {
    return {
      shouldRoute: false,
      reason: 'already_owning',
      employee: winner.employee,
      winnerScore,
      secondScore,
      source: 'deterministic',
    };
  }

  const currentScore =
    scored.find((row) => row.employee.employee_id.trim() === currentId)?.score ?? 0;
  if (winnerScore - currentScore < MIN_MARGIN) {
    return {
      shouldRoute: false,
      reason: 'current_still_competitive',
      employee: winner.employee,
      winnerScore,
      secondScore: currentScore,
      source: 'deterministic',
      ambiguous: true,
    };
  }

  return {
    shouldRoute: true,
    reason: `role_${normalizeTeammateRole(winner.employee.role)}`,
    employee: winner.employee,
    fromEmployeeId: currentId,
    fromName: currentEmployee?.name.trim() || 'teammate',
    winnerScore,
    secondScore,
    source: 'deterministic',
  };
}
