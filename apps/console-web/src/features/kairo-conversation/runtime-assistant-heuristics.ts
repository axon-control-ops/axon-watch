const OPEN_STYLE_RE =
  /\b(why|how|explain|tell me (?:more|about)|what happened|what went wrong|walk me through|can you elaborate|help me understand|what do you think|should we|could you help)\b/i;

const STATUS_STYLE_RE =
  /\b(approval|approvals|attention|status|briefing|fleet|health|signal|signals|running|active run|what needs|nominal|degraded|clear)\b/i;

const COMMAND_STYLE_RE =
  /\b(git status|check health|run\s+\S+|open attention|focus attention|switch to|dispatch|handoff|hand it off|resume)\b/i;

// Leadership/capability questions deserve VAXON's consultative model. In
// particular, "help me run the school" must never be downgraded to a check of
// the technical run queue merely because it contains the word "run".
const CONSULTATIVE_STYLE_RE =
  /\b(?:will|can|could|should)\b[\s\S]{0,180}\b(?:help|support|advise|suggest|recommend|manage|coordinate|prepare|grade|assess|run)\b/i;

export function shouldPrimeRuntimeAssistantCue(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (CONSULTATIVE_STYLE_RE.test(trimmed)) {
    return true;
  }
  if (COMMAND_STYLE_RE.test(trimmed) || STATUS_STYLE_RE.test(trimmed)) {
    return false;
  }
  return OPEN_STYLE_RE.test(trimmed);
}

export const RUNTIME_ASSISTANT_CUE_LINE =
  "One moment - I'm checking that with the runtime for you.";

export const RUNTIME_ASSISTANT_CUE_COPY =
  'Checking that with the runtime now...';
