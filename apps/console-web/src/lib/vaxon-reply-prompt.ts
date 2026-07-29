/** Detect when a spoken line expects an operator reply (VAXON or teammate). */

const REPLY_INTENT_RE =
  /\b(shall i|shall we|what shall|would you like(?: me to)?|do you want(?: me to)?|want me to|open attention for|confirm|approve|retry|try again|your call|focus on)\b/i;

const RETRY_INTENT_RE = /\b(try again|retry(?:\s+that)?(?:\s+bounded)?(?:\s+shift)?)\b/i;

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

export function spokenLineAsksForRetry(line: string | null | undefined): boolean {
  return RETRY_INTENT_RE.test(String(line ?? ''));
}

export function isAffirmativeOperatorReply(message: string | null | undefined): boolean {
  const text = String(message ?? '').trim().toLowerCase();
  if (!text) {
    return false;
  }
  return /^(yes|y|yeah|yep|sure|ok|okay|do it|go ahead|continue|try again|retry)(?:[!.\s].*)?$/i.test(
    text,
  );
}

export function vaxonAffirmReplyCta(line: string | null | undefined): string {
  const text = String(line ?? '');
  if (spokenLineAsksForRetry(text)) {
    return 'Try again';
  }
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
