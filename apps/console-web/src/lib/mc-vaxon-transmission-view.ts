/** Pure helpers for the Mission Control VAXON Transmission card (right dock). */

export type VaxonTransmissionMode = 'standby' | 'transmitting' | 'locked';

export type VaxonTransmissionView = {
  mode: VaxonTransmissionMode;
  eyebrow: string;
  body: string;
  empty: boolean;
};

export function resolveVaxonTransmissionView(input: {
  spokenText?: string | null;
  conversationReply?: string | null;
  speaking?: boolean;
  pending?: boolean;
}): VaxonTransmissionView {
  const spoken = input.spokenText?.trim() || '';
  const reply = input.conversationReply?.trim() || '';
  const body = spoken || reply;

  if (!body) {
    return {
      mode: input.pending ? 'transmitting' : 'standby',
      eyebrow: input.pending ? 'Channel open' : 'Awaiting transmission',
      body: input.pending
        ? 'VAXON is working that request…'
        : 'Ask VAXON here — replies land in this dock.',
      empty: true,
    };
  }

  if (input.speaking || input.pending) {
    return {
      mode: 'transmitting',
      eyebrow: 'Live transmission',
      body,
      empty: false,
    };
  }

  return {
    mode: 'locked',
    eyebrow: 'Last transmission',
    body,
    empty: false,
  };
}
