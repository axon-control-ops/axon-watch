/** Heuristics for hands-free follow-ups during the post-reply conversation window. */

const AMBIENT_CHATTER_RE =
  /\b(game last night|the weather|nice weather|soccer|football game|movie tonight|what'?s for dinner|did you see)\b/i;

const FOLLOWUP_CUE_RE =
  /\b(and|also|what about|how about|tell me more|anything else|more on|about that|same for|same with|then|next|too|repeat|say that again|say it again|one more time|again)\b/i;

const QUESTION_START_RE =
  /^(what|who|where|when|why|how|is|are|can|could|does|did|will|would|should)\b/i;

/** Natural requests that often start with filler ("okay can you…"). */
const OPERATOR_REQUEST_RE =
  /\b(can you|could you|would you|will you|please|tell me|show me|give me|i need|i want|walk me|check on|look at)\b/i;

const QUESTION_ANYWHERE_RE = /\b(what|who|where|when|why|how)\b/i;

export function looksLikeOperatorFollowUp(text: string): boolean {
  const normalized = text.trim();
  if (normalized.length < 3) {
    return false;
  }
  if (AMBIENT_CHATTER_RE.test(normalized)) {
    return false;
  }
  if (FOLLOWUP_CUE_RE.test(normalized)) {
    return true;
  }
  if (QUESTION_START_RE.test(normalized)) {
    return true;
  }
  if (OPERATOR_REQUEST_RE.test(normalized)) {
    return true;
  }
  if (QUESTION_ANYWHERE_RE.test(normalized)) {
    return true;
  }
  if (normalized.endsWith('?')) {
    return true;
  }
  // Short clarifications: "and DashPro", "DashPro too", "approve it"
  return normalized.length <= 48;
}
