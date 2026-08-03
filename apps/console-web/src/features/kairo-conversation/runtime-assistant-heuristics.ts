const OPEN_STYLE_RE =
  /\b(why|how|explain|tell me (?:more|about)|what happened|what went wrong|walk me through|can you elaborate|help me understand|what do you think|should we|could you help)\b/i;

/** Live ops / fleet questions must stay on the fast status path — not chatbot filler. */
const STATUS_STYLE_RE =
  /\b(approval|approvals|attention|status|briefing|fleet|health|signal|signals|critical|issue|issues|running|active run|what needs|nominal|degraded|clear|dashpro|sentry|ci)\b/i;

const COMMAND_STYLE_RE =
  /\b(git status|check health|run\s+\S+|open attention|focus attention|switch to|dispatch|handoff|hand it off|resume)\b/i;

export function shouldPrimeRuntimeAssistantCue(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (COMMAND_STYLE_RE.test(trimmed) || STATUS_STYLE_RE.test(trimmed)) {
    return false;
  }
  return OPEN_STYLE_RE.test(trimmed);
}

/** Spoken-only filler while a deep ask is in flight — never the Live Transmission answer. */
export const RUNTIME_ASSISTANT_CUE_LINE =
  'One moment — pulling verified runtime evidence.';

/** @deprecated Keep for tests/imports; do not write this into Live Transmission. */
export const RUNTIME_ASSISTANT_CUE_COPY =
  'One moment — pulling verified runtime evidence.';
