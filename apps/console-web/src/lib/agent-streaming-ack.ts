/** Contextual streaming ack — never a fake model reply like bare "On it…". */

export type AgentAddressForm = 'sir' | 'Sir King' | null;

const NUMBER_WORDS: Record<string, string> = {
  '0': 'zero',
  '1': 'one',
  '2': 'two',
  '3': 'three',
  '4': 'four',
  '5': 'five',
  '6': 'six',
  '7': 'seven',
  '8': 'eight',
  '9': 'nine',
  '10': 'ten',
};

function withAddress(line: string, address: AgentAddressForm): string {
  if (!address) {
    return line;
  }
  if (/\b(sir|sir king)\b/i.test(line)) {
    return line;
  }
  // Prefer mid-sentence address so it sounds spoken, not stamped.
  if (/[.!?]$/.test(line)) {
    return `${line.slice(0, -1)}, ${address}${line.slice(-1)}`;
  }
  return `${line}, ${address}.`;
}

function intentHint(prompt: string): string | null {
  const flat = prompt.replace(/\s+/g, ' ').trim();
  if (!flat) {
    return null;
  }
  if (/\breceipts?\b/i.test(flat) || /\blast shift\b/i.test(flat)) {
    return 'Pulling the shift receipts now';
  }
  if (/\bsentry\b/i.test(flat)) {
    return 'Looking at that Sentry alert now';
  }
  if (/\breport\b|\bstand-?up\b|\bstatus\b/i.test(flat)) {
    return 'Building the stand-up now';
  }
  if (/\breview\b|\bcritical review\b/i.test(flat)) {
    return 'Working the review now';
  }
  if (/\bwalk me through\b|\bexplain\b|\bsummarize\b/i.test(flat)) {
    return 'Walking that through now';
  }
  if (/\bfix\b|\bpatch\b|\brepair\b/i.test(flat)) {
    return 'Working the fix now';
  }
  return null;
}

/**
 * Short UI placeholder while the model stream has not produced speakable copy yet.
 * Prefer real thinking/reply text over this whenever available.
 */
export function buildStreamingAckLine(input: {
  operatorPrompt?: string | null;
  address?: AgentAddressForm;
}): string {
  const hint = intentHint(String(input.operatorPrompt ?? ''));
  const base = hint ?? 'Working that now';
  return withAddress(base, input.address ?? null);
}

/** Employee agents address the operator as Sir King; VAXON uses sir. */
export function addressFormForSpeaker(kind: 'vaxon' | 'employee' | string | null | undefined): AgentAddressForm {
  if (kind === 'employee') {
    return 'Sir King';
  }
  if (kind === 'vaxon') {
    return 'sir';
  }
  return null;
}

/** Keep digit+role phrases speakable in ack lines if a count slips in. */
export function softenAckCountsForSpeech(text: string): string {
  return text.replace(/\b(\d{1,2})\s+([A-Z][A-Za-z-]+)\b/g, (_full, digits: string, word: string) => {
    const spoken = NUMBER_WORDS[digits] ?? digits;
    return `${spoken} ${word}`;
  });
}
