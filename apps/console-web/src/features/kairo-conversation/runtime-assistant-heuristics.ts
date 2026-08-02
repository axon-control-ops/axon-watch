const OPEN_STYLE_RE =
  /\b(why|how|explain|tell me (?:more|about)|what happened|what went wrong|walk me through|can you elaborate|help me understand|what do you think|should we|could you help)\b/i;

const STATUS_STYLE_RE =
  /\b(approval|approvals|attention|status|briefing|fleet|health|signal|signals|running|active run|what needs|nominal|degraded|clear)\b/i;

const COMMAND_STYLE_RE =
  /\b(git status|check health|run\s+\S+|open attention|focus attention|switch to|dispatch|handoff|hand it off|resume)\b/i;

/** Long / charter-shaped prompts need Ask runtime so Chief of Staff policy applies. */
const CHIEF_OF_STAFF_RUNTIME_RE =
  /\b(chief of staff|executive intelligence|mission lifecycle|autonomy levels|you are vaxon)\b/i;

const COS_RUNTIME_MIN_CHARS = 480;

export function shouldPrimeRuntimeAssistantCue(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (CHIEF_OF_STAFF_RUNTIME_RE.test(trimmed) || trimmed.length >= COS_RUNTIME_MIN_CHARS) {
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
