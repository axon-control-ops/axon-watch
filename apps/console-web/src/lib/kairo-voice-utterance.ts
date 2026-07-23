/** Pub/sub for the text currently being spoken — Galaxy captions + speaker avatar. */

export type KairoVoiceSpeakerKind = 'vaxon' | 'employee';

export type KairoVoiceSpeaker = {
  kind: KairoVoiceSpeakerKind;
  id: string;
  name: string;
  roleLabel?: string | null;
  azureVoiceId?: string | null;
};

export type KairoVoiceUtteranceState = {
  text: string | null;
  speaker: KairoVoiceSpeaker | null;
};

export type KairoVoiceUtteranceListener = (state: KairoVoiceUtteranceState) => void;

const utteranceListeners = new Set<KairoVoiceUtteranceListener>();
let currentUtterance: KairoVoiceUtteranceState = { text: null, speaker: null };

export function vaxonVoiceSpeaker(
  overrides?: Partial<Omit<KairoVoiceSpeaker, 'kind' | 'id'>>,
): KairoVoiceSpeaker {
  return {
    kind: 'vaxon',
    id: 'vaxon',
    name: overrides?.name?.trim() || 'VAXON',
    roleLabel: overrides?.roleLabel ?? 'Operator console',
    azureVoiceId: overrides?.azureVoiceId ?? null,
  };
}

export function employeeVoiceSpeaker(employee: {
  employee_id: string;
  name: string;
  role_label?: string | null;
  role?: string | null;
  azure_voice_id?: string | null;
}): KairoVoiceSpeaker {
  return {
    kind: 'employee',
    id: employee.employee_id,
    name: employee.name.trim() || 'Teammate',
    roleLabel: employee.role_label?.trim() || employee.role?.trim() || 'Agent',
    azureVoiceId: employee.azure_voice_id ?? null,
  };
}

export function getKairoVoiceUtterance(): string | null {
  return currentUtterance.text;
}

export function getKairoVoiceSpeaker(): KairoVoiceSpeaker | null {
  return currentUtterance.speaker;
}

export function getKairoVoiceUtteranceState(): KairoVoiceUtteranceState {
  return currentUtterance;
}

export function notifyKairoVoiceUtterance(
  text: string | null,
  speaker: KairoVoiceSpeaker | null = null,
): void {
  const nextText = text?.trim() ? text.trim() : null;
  const nextSpeaker = nextText ? speaker : null;
  if (
    nextText === currentUtterance.text &&
    nextSpeaker?.id === currentUtterance.speaker?.id &&
    nextSpeaker?.kind === currentUtterance.speaker?.kind
  ) {
    return;
  }
  currentUtterance = { text: nextText, speaker: nextSpeaker };
  // #region agent log
  if (typeof fetch === 'function') {
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'speaker-avatar',hypothesisId:'C',location:'kairo-voice-utterance.ts:notifyKairoVoiceUtterance',message:'utterance state published',data:{hasText:Boolean(nextText),speakerKind:nextSpeaker?.kind??null,speakerId:nextSpeaker?.id??null,listenerCount:utteranceListeners.size},timestamp:Date.now()})}).catch(()=>{});
  }
  // #endregion
  for (const listener of utteranceListeners) {
    listener(currentUtterance);
  }
}

export function subscribeKairoVoiceUtterance(
  listener: KairoVoiceUtteranceListener,
): () => void {
  utteranceListeners.add(listener);
  listener(currentUtterance);
  return () => {
    utteranceListeners.delete(listener);
  };
}

/** Test helper — clear utterance pub/sub state. */
export function resetKairoVoiceUtteranceForTests(): void {
  currentUtterance = { text: null, speaker: null };
  utteranceListeners.clear();
}
