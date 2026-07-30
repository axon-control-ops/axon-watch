/** Expand bare REPORT / status hotwords into a full second-brain stand-up ask. */

const REPORT_HOTWORD_RE =
  /^(?:report|status(?:\s+report)?|update|stand[\s-]?up|where\s+do\s+we\s+stand|where\s+are\s+we(?:\s+now)?|what(?:'?s| is)\s+(?:going\s+on|happening))\s*[.!]?\s*$/i;

export const REPORT_EXPANDED_PROMPT =
  'REPORT — give me a second-brain stand-up. ' +
  'Cover Attention (what needs me now), Work in flight (runs and busy teammates by name if known), ' +
  'Fleet (anything off-nominal), then one clear Next move. ' +
  'Speak like my colleague: conversational, dry wit, no semicolon dumps, no robotic status chrome. ' +
  'Spell out small counts before words like Lead so speech does not glue them.';

/** Returns an expanded prompt when the operator used a report hotword; otherwise null. */
export function expandReportHotword(content: string): string | null {
  const trimmed = content.trim();
  if (!trimmed || !REPORT_HOTWORD_RE.test(trimmed)) {
    return null;
  }
  return REPORT_EXPANDED_PROMPT;
}
