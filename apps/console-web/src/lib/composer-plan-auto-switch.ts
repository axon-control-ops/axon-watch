/**
 * Cursor-aligned Plan mode routing for Agent submits.
 *
 * Cursor docs: Plan is suggested for complex/keyword tasks; entry is normally
 * explicit (Shift+Tab / mode picker). Cursor does NOT force-switch on long
 * executable checklists. Axon-X matches that and improves it:
 * - explicit "write/make a plan" → switch to Plan
 * - clear execution directives (do / re-fan-out / fix / report…) → stay Agent
 * - ambiguous planning asks → offer Plan, pause until Use Plan | Stay in Agent
 */

import { isBuildPlanImplementPrompt } from './build-plan-prompt';

export type PlanAutoSwitchAction = 'stay' | 'switch' | 'offer';

export type PlanAutoSwitchDecision = {
  action: PlanAutoSwitchAction;
  reason: string;
  /** @deprecated Prefer `action === 'switch'`. Kept for older call sites/tests. */
  shouldSwitch: boolean;
};

/** Explicit requests to produce a plan always win over execution vocabulary. */
const EXPLICIT_PLAN_REQUESTS = [
  /\bmake a plan\b/i,
  /\bwrite a plan\b/i,
  /\bdraft a plan\b/i,
  /\bcreate a plan\b/i,
  /\bproduce a plan\b/i,
  /\bplan (this|out|the approach)\b/i,
  /^\s*(?:please\s+)?plan for\b/i,
];

/** Ambiguous analysis — suggest Plan, do not force when execution is clear. */
const PLANNING_PHRASES = [
  /\bhow should we\b/i,
  /\btrade-?offs?\b/i,
  /\barchitecture\b/i,
  /\bdesign (this|the|a)\b/i,
  /\bstep[- ]by[- ]step\b/i,
  /\bbreak (this|it) down\b/i,
  /\bapproach (for|to)\b/i,
  /\bwhat('s| is) the (best )?plan\b/i,
];

/** Mentions of an existing plan while asking for execution — stay in Agent. */
const EXECUTION_PLAN_MENTION = [
  /\b(build|implement|execute|expand|update|edit|revise|follow|apply)\b[\s\S]{0,80}\b(the |this |that |saved )?plan\b/i,
  /\b(the |this |that |saved )?plan\b[\s\S]{0,80}\b(build|implement|execute|expand|update|edit|revise|follow|apply)\b/i,
  /\b(according to|using|from|in) (the |this |that |saved )?plan\b/i,
  /\bplan (file|artifact|doc|document)\b/i,
];

/**
 * Imperative / operational directives — long multi-step orders stay in Agent
 * (Cursor keeps Agent for executable work; Plan is for approach review).
 */
const EXECUTION_DIRECTIVES = [
  /\b(do this|do the following|re-?fan-?out|fan-?out|execute|implement|fix|retry|re-?run|dispatch|assign|confirm|leave\b.*\buncommitted|report (again|back)|when auth is fixed|cursor auth)\b/i,
  /\b(don'?t|do not)\s+(write|make|draft)\s+a\s+plan\b/i,
  /\brun ids?\b/i,
  /\bthread evidence\b/i,
];

const BULLET_LINE = /^\s*(?:[-*•]|\d+[.)])\s+/;

function hasExecutionDirective(text: string): boolean {
  if (EXECUTION_DIRECTIVES.some((pattern) => pattern.test(text))) {
    return true;
  }
  // Numbered operational checklist with imperative verbs on most lines.
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const bullets = lines.filter((line) => BULLET_LINE.test(line));
  if (bullets.length < 2) {
    return false;
  }
  const imperative = bullets.filter((line) =>
    /\b(do|fix|retry|confirm|leave|report|re-?fan|fan-out|assign|check|verify|open|send|keep|stop|start|clear|cancel)\b/i.test(
      line,
    ),
  );
  return imperative.length >= Math.ceil(bullets.length * 0.5);
}

function stay(reason: string): PlanAutoSwitchDecision {
  return { action: 'stay', reason, shouldSwitch: false };
}

function switchToPlan(reason: string): PlanAutoSwitchDecision {
  return { action: 'switch', reason, shouldSwitch: true };
}

function offerPlan(reason: string): PlanAutoSwitchDecision {
  return { action: 'offer', reason, shouldSwitch: false };
}

export function shouldSoftSwitchAgentToPlan(
  composerMode: string,
  promptText: string,
): PlanAutoSwitchDecision {
  if (composerMode !== 'agent') {
    return stay('mode_not_agent');
  }
  const text = String(promptText || '').trim();
  if (!text) {
    return stay('empty_prompt');
  }

  // Build Plan seeds a long plan-shaped prompt on purpose — never bounce to Plan.
  if (isBuildPlanImplementPrompt(text)) {
    return stay('build_plan_implement');
  }

  if (EXPLICIT_PLAN_REQUESTS.some((pattern) => pattern.test(text))) {
    return switchToPlan('explicit_plan_request');
  }

  if (EXECUTION_PLAN_MENTION.some((pattern) => pattern.test(text))) {
    return stay('execution_plan_mention');
  }

  // Executable orders (incl. long Dana-style corrections) stay in Agent.
  if (hasExecutionDirective(text)) {
    return stay('execution_directive');
  }

  for (const pattern of PLANNING_PHRASES) {
    if (pattern.test(text)) {
      return offerPlan('planning_phrase');
    }
  }

  const lines = text.split(/\r?\n/);
  const bulletCount = lines.filter((line) => BULLET_LINE.test(line)).length;
  if (bulletCount >= 3) {
    // Structured list without clear imperatives — offer, don't force.
    return offerPlan('bullet_heavy');
  }

  if (text.length >= 420 && /\b(then|steps?|phases?|first|next|finally)\b/i.test(text)) {
    // Cursor suggests for complex tasks; we offer instead of silent switch.
    return offerPlan('long_multistep');
  }

  return stay('no_match');
}
