/** Heuristics for hands-free follow-ups during the post-reply conversation window. */

const AMBIENT_CHATTER_RE =
  /\b(game last night|the weather|nice weather|soccer|football game|movie tonight|what'?s for dinner|did you see)\b/i;

const FOLLOWUP_CUE_RE =
  /\b(and|also|what about|how about|tell me more|anything else|more on|about that|same for|same with|then|next|too|repeat|say that again|say it again|one more time|again)\b/i;

const QUESTION_START_RE =
  /^(what|who|where|when|why|how|is|are|can|could|does|did|will|would|should)\b/i;

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
  if (normalized.endsWith('?')) {
    return true;
  }
  // Short clarifications: "and DashPro", "DashPro too"
  return normalized.length <= 36;
}
