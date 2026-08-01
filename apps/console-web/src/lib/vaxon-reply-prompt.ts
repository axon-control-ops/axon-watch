/** Detect when a spoken line expects an operator reply (VAXON or teammate). */

const REPLY_INTENT_RE =
  /\b(shall i|shall we|what shall|would you like(?: me to)?|do you want(?: me to)?|want me to|open attention for|confirm|approve|retry|try again|your call|focus on)\b/i;

/** Operator must act — handoff, switch workspace, decide, or unblock. */
const INTERVENTION_INTENT_RE =
  /\b(handoff|switch there|needs? you|need your|waiting for (?:your|the operator)|your go-ahead|paused and waiting|finish ['"]|switch (?:to|there)|operator (?:must|should)|unblock)\b/i;

const RETRY_INTENT_RE = /\b(try again|retry(?:\s+that)?(?:\s+bounded)?(?:\s+shift)?)\b/i;

export function vaxonLineNeedsIntervention(line: string | null | undefined): boolean {
  const text = String(line ?? '').trim();
  if (!text) {
    return false;
  }
  return INTERVENTION_INTENT_RE.test(text);
}

export function vaxonLineAsksForReply(line: string | null | undefined): boolean {
  const text = String(line ?? '').trim();
  if (!text) {
    return false;
  }
  if (/\?\s*$/.test(text)) {
    return true;
  }
  if (REPLY_INTENT_RE.test(text)) {
    return true;
  }
  // Handoff / "switch there" / needs-you lines also need a top CTA.
  return vaxonLineNeedsIntervention(text);
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
  if (/\bhandoff\b/i.test(text) || /\bswitch there\b/i.test(text)) {
    return 'Yes — switch & attend';
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
