/** Pure helpers for the Mission Control VAXON Transmission card (right dock). */

import { normalizeKairoCopy } from './kairo-entity-labels';

export type VaxonTransmissionMode = 'standby' | 'transmitting' | 'locked';

export type VaxonTransmissionView = {
  mode: VaxonTransmissionMode;
  eyebrow: string;
  body: string;
  /** Short map line when body is a mega briefing dump. */
  summary: string;
  /** Extra sentences collapsed under “Show detail”. */
  detailLines: string[];
  empty: boolean;
};

const SUMMARY_MAX = 180;

/** Split a mega spoken briefing into a map + detail bullets. */
export function splitTransmissionBody(body: string): {
  summary: string;
  detailLines: string[];
} {
  const cleaned = body.replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return { summary: '', detailLines: [] };
  }
  // Split on sentence boundaries only — a character-class bug once treated
  // every capital letter as a new sentence ("Dana here." → 10-char summary).
  const parts = cleaned
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length <= 1 && cleaned.length <= SUMMARY_MAX) {
    return { summary: cleaned, detailLines: [] };
  }
  const summary = parts[0] || cleaned;
  const detailLines = parts.slice(1).filter((part) => part !== summary);
  if (summary.length > SUMMARY_MAX) {
    return {
      summary: `${summary.slice(0, SUMMARY_MAX - 1).trimEnd()}…`,
      detailLines: [summary, ...detailLines].filter(
        (part, index, all) => all.indexOf(part) === index,
      ),
    };
  }
  return { summary, detailLines };
}

export function resolveVaxonTransmissionView(input: {
  spokenText?: string | null;
  conversationReply?: string | null;
  speaking?: boolean;
  pending?: boolean;
}): VaxonTransmissionView {
  const spoken = normalizeKairoCopy(input.spokenText?.trim() || '');
  const reply = normalizeKairoCopy(input.conversationReply?.trim() || '');
  const body = spoken || reply;

  if (!body) {
    return {
      mode: input.pending ? 'transmitting' : 'standby',
      eyebrow: input.pending ? 'Channel open' : 'Awaiting transmission',
      body: input.pending
        ? 'VAXON is working that request…'
        : 'Ask your second brain — or say REPORT for a stand-up.',
      summary: input.pending
        ? 'VAXON is working that request…'
        : 'Ask your second brain — or say REPORT for a stand-up.',
      detailLines: [],
      empty: true,
    };
  }

  const { summary, detailLines } = splitTransmissionBody(body);
  const mode: VaxonTransmissionMode =
    input.speaking || input.pending ? 'transmitting' : 'locked';

  return {
    mode,
    eyebrow: mode === 'transmitting' ? 'Live transmission' : 'Last transmission',
    body,
    summary,
    detailLines,
    empty: false,
  };
}
