/** Lead stand-up / status report — cinematic card sibling of Lead Decompose. */

export type LeadStandupCard = {
  leadName: string;
  title: string;
  intro: string;
  bodyMarkdown: string;
  confidence: string | null;
  verificationNotice: string | null;
};

const STAND_RE =
  /\*{0,2}here['’]?s where things stand\*{0,2}/i;
const CONFIDENCE_RE = /\bConfidence:\s*(\d{1,2})\s*\/\s*10\b/i;
const VERIFICATION_RE =
  /\*{0,2}Verification notice:\*{0,2}\s*([\s\S]+)$/i;

export function looksLikeLeadStandupReport(text: string): boolean {
  const trimmed = String(text || '').trim();
  if (!trimmed || trimmed.length < 80) {
    return false;
  }
  if (!STAND_RE.test(trimmed) && !/\bOpen risk\b/i.test(trimmed)) {
    return false;
  }
  return CONFIDENCE_RE.test(trimmed) || /^\|.+\|/m.test(trimmed);
}

export function parseLeadStandupReport(
  text: string,
  options: { leadName?: string | null } = {},
): LeadStandupCard | null {
  const trimmed = String(text || '').trim();
  if (!looksLikeLeadStandupReport(trimmed)) {
    return null;
  }

  let body = trimmed;
  let verificationNotice: string | null = null;
  const verificationMatch = body.match(VERIFICATION_RE);
  if (verificationMatch) {
    verificationNotice = verificationMatch[1]?.trim() || null;
    body = body.slice(0, verificationMatch.index).trim();
  }

  let confidence: string | null = null;
  const confidenceMatch = body.match(CONFIDENCE_RE);
  if (confidenceMatch) {
    confidence = `${confidenceMatch[1]}/10`;
    body = body.replace(CONFIDENCE_RE, '').trim();
  }

  // Drop trailing horizontal rules left after confidence/notice extraction.
  body = body.replace(/\n-{3,}\s*$/g, '').trim();

  const standMatch = body.match(STAND_RE);
  let intro = body;
  let bodyMarkdown = body;
  if (standMatch?.index != null) {
    intro = body.slice(0, standMatch.index).trim();
    bodyMarkdown = body.slice(standMatch.index).trim();
  }

  const leadName = String(options.leadName || '').trim() || 'Lead';
  return {
    leadName,
    title: 'Stand-up',
    intro,
    bodyMarkdown,
    confidence,
    verificationNotice,
  };
}
