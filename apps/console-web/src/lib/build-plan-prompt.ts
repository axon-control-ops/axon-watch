import { displayPlanTitle } from './plan-display-title';

const PLAN_BODY_COMPOSER_MAX = 14_000;

/** Marker line used by Build Plan; soft Plan auto-switch must ignore these prompts. */
const BUILD_PLAN_PROMPT_RE = /^Build this plan \([^)]+\):/i;

export function isBuildPlanImplementPrompt(promptText: string): boolean {
  return BUILD_PLAN_PROMPT_RE.test(String(promptText || '').trim());
}

export function buildImplementPlanPrompt(input: {
  planId: string;
  title: string;
  content: string;
}): string {
  const planId = input.planId.trim();
  const title = displayPlanTitle(input.title, 'Saved plan');
  const body = input.content.trim();
  const clipped =
    body.length > PLAN_BODY_COMPOSER_MAX
      ? `${body.slice(0, PLAN_BODY_COMPOSER_MAX)}\n\n…(plan truncated for composer; full artifact ${planId})`
      : body;

  return [
    `Build this plan (${planId}): ${title}`,
    '',
    'Implement the plan steps in order. Prefer the smallest change that satisfies each step.',
    'Do not expand scope beyond the plan. Follow the verification checklist when finishing.',
    '',
    '---',
    clipped,
    '---',
  ].join('\n');
}
