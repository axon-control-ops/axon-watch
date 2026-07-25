/** Sanitize plan card titles so exploratory openers never look like the artifact name. */
const WEAK_PLAN_TITLE_RE =
  /^(i'?ll|i will|i am|i'?m|let me|looking|gathering|drafting|searching|checking|reading|i have enough|the request)\b/i;

export function displayPlanTitle(title: string, fallback = 'Saved plan'): string {
  const trimmed = title.trim().replace(/\s+/g, ' ');
  if (!trimmed || WEAK_PLAN_TITLE_RE.test(trimmed)) {
    return fallback;
  }
  return trimmed;
}
