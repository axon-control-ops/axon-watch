/**
 * Deterministic heuristic for soft-switching Agent → Plan (Cursor-like).
 * No model call — keywords, length, and list structure only.
 */

import { isBuildPlanImplementPrompt } from './build-plan-prompt';

export type PlanAutoSwitchDecision = {
  shouldSwitch: boolean;
  reason: string;
};

const PLAN_PHRASES = [
  /\bhow should we\b/i,
  /\btrade-?offs?\b/i,
  /\barchitecture\b/i,
  /\bdesign (this|the|a)\b/i,
  /\bmake a plan\b/i,
  /\bwrite a plan\b/i,
  /\bstep[- ]by[- ]step\b/i,
  /\bbreak (this|it) down\b/i,
  /\bapproach (for|to)\b/i,
  /\bwhat('s| is) the (best )?plan\b/i,
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

  if (/\bplan\b/i.test(text) && text.length >= 80) {
    return { shouldSwitch: true, reason: 'plan_keyword' };
  }

  return { shouldSwitch: false, reason: 'no_match' };
}
