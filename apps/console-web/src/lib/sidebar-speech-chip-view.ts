/** Sticky spoken-line state for the IDE left-rail speech chip. */

import type { KairoVoiceSpeaker } from './kairo-voice-utterance';

export type SidebarSpeechChipView = {
  statusLabel: string;
  displayText: string;
  empty: boolean;
};

export function sidebarSpeechCanExpand(text: string): boolean {
  const normalized = text.trim();
  if (!normalized) {
    return false;
  }
  // Collapsed chip now shows ~14 lines; only offer More for longer stand-ups.
  return normalized.length > 420 || normalized.split(/\r?\n/).length > 12;
}

export function resolveSidebarSpeechChipView(input: {
  spokenText: string | null | undefined;
  speaker: KairoVoiceSpeaker | null | undefined;
  speaking: boolean;
  fallbackPersonaName: string;
  stickyText?: string;
  stickySpeakerName?: string;
}): SidebarSpeechChipView & { stickyText: string; stickySpeakerName: string } {
  const next = input.spokenText?.trim() ?? '';
  let stickyText = input.stickyText?.trim() ?? '';
  let stickySpeakerName = input.stickySpeakerName?.trim() ?? '';
  if (next) {
    stickyText = next;
    stickySpeakerName =
      input.speaker?.name?.trim() || input.fallbackPersonaName.trim() || 'Agent';
  }
  const displayText = stickyText || next;
  const speakerLabel =
    stickySpeakerName || input.speaker?.name?.trim() || input.fallbackPersonaName.trim() || 'Agent';
  let statusLabel = `${speakerLabel} · voice`;
  if (input.speaking) {
    statusLabel = `${speakerLabel} · speaking`;
  } else if (displayText) {
    statusLabel = `${speakerLabel} · last spoken`;
  }
  return {
    statusLabel,
    displayText,
    empty: !displayText,
    stickyText,
    stickySpeakerName,
  };
}
