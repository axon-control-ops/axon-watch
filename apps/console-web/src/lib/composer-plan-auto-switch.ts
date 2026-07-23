/**
 * Deterministic heuristic for soft-switching Agent → Plan (Cursor-like).
 * No model call — explicit planning intent only. Bare "plan" is not enough:
 * operators often say "the plan", "expand the plan", or "use the plan file"
 * while meaning Agent execution.
 */

import { isBuildPlanImplementPrompt } from './build-plan-prompt';

export type PlanAutoSwitchDecision = {
  shouldSwitch: boolean;
  reason: string;
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

/** Other signals that the operator wants analysis rather than execution. */
const PLAN_PHRASES = [
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

const BULLET_LINE = /^\s*(?:[-*•]|\d+[.)])\s+/;

export function shouldSoftSwitchAgentToPlan(
  composerMode: string,
  promptText: string,
): PlanAutoSwitchDecision {
  if (composerMode !== 'agent') {
    return { shouldSwitch: false, reason: 'mode_not_agent' };
  }
  const text = String(promptText || '').trim();
  if (!text) {
    return { shouldSwitch: false, reason: 'empty_prompt' };
  }

  // Build Plan seeds a long plan-shaped prompt on purpose — never bounce it back to Plan.
  if (isBuildPlanImplementPrompt(text)) {
    return { shouldSwitch: false, reason: 'build_plan_implement' };
  }

  if (EXPLICIT_PLAN_REQUESTS.some((pattern) => pattern.test(text))) {
    return { shouldSwitch: true, reason: 'planning_phrase' };
  }

  if (EXECUTION_PLAN_MENTION.some((pattern) => pattern.test(text))) {
    return { shouldSwitch: false, reason: 'execution_plan_mention' };
  }

  for (const pattern of PLAN_PHRASES) {
    if (pattern.test(text)) {
      return { shouldSwitch: true, reason: 'planning_phrase' };
    }
  }

  const lines = text.split(/\r?\n/);
  const bulletCount = lines.filter((line) => BULLET_LINE.test(line)).length;
  if (bulletCount >= 3) {
    return { shouldSwitch: true, reason: 'bullet_heavy' };
  }

  if (text.length >= 420 && /\b(then|steps?|phases?|first|next|finally)\b/i.test(text)) {
    return { shouldSwitch: true, reason: 'long_multistep' };
  }

  // Bare "plan" alone is too common for Agent work (file names, "the plan", etc.).
  return { shouldSwitch: false, reason: 'no_match' };
}
