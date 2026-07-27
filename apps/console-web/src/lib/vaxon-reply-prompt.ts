/** Detect when a VAXON spoken line expects an operator reply. */

const REPLY_INTENT_RE =
  /\b(shall i|shall we|what shall|would you like(?: me to)?|do you want(?: me to)?|want me to|open attention for|confirm|approve|retry|focus on)\b/i;

export function vaxonLineAsksForReply(line: string | null | undefined): boolean {
  const text = String(line ?? '').trim();
  if (!text) {
    return false;
  }
  if (/\?\s*$/.test(text)) {
    return true;
  }
  return REPLY_INTENT_RE.test(text);
}

export function vaxonAffirmReplyCta(line: string | null | undefined): string {
  const text = String(line ?? '');
  if (/\bopen attention\b/i.test(text)) {
    return 'Yes — open Attention';
  }
  if (/\btriage\b/i.test(text)) {
    return 'Yes — triage';
  }
  if (/\bdiagnos/i.test(text)) {
    return 'Yes — diagnose';
  }
  return 'Yes — continue';
}
