/** Strip literal spoken symbol/punctuation names before TTS. */

const LITERAL_SYMBOL_WORD_RES: RegExp[] = [
  /\bsmiley\s+face\b/gi,
  /\bgrinning\s+face\b/gi,
  /\bwinking\s+face\b/gi,
  /\bemoji\b/gi,
  /\bback\s*slash(?:es)?\b/gi,
  /\bforward\s+slash(?:es)?\b/gi,
  /\bhash\s+sign(?:s)?\b/gi,
  /\bcolon(?:s)?\b/gi,
  /\bslash(?:es)?\b/gi,
  /\bunderscore(?:s)?\b/gi,
  /\basterisk(?:s)?\b/gi,
  /\bhashtag(?:s)?\b/gi,
];

/** Remove spoken punctuation/symbol names the model may emit literally. */
export function stripLiteralSymbolWords(text: string): string {
  let out = String(text || '');
  if (!out) {
    return '';
  }
  for (const pattern of LITERAL_SYMBOL_WORD_RES) {
    out = out.replace(pattern, ' ');
  }
  return out
    .replace(/\s+,/g, ',')
    .replace(/,\s*,+/g, ',')
    .replace(/\s{2,}/g, ' ')
    .replace(/^[ ,]+|[ ,]+$/g, '')
    .trim();
}
