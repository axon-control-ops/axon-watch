/**
 * Explicit duplex conversation phases for continuous VAXON.
 * The 30-second follow-up window remains a policy value (see kairo-voice-followup-window).
 */

import { KAIRO_VOICE_FOLLOWUP_WINDOW_MS } from '../../lib/kairo-voice-followup-window';

export type DuplexConversationPhase =
  | 'idle'
  | 'wake_listening'
  | 'transcribing'
  | 'thinking'
  | 'speaking'
  | 'followup_ready'
  | 'privacy_muted'
  | 'alerting';

/** Re-export so duplex callers share one policy constant with the follow-up window. */
export const DUPLEX_FOLLOWUP_WINDOW_MS = KAIRO_VOICE_FOLLOWUP_WINDOW_MS;

export function mapLegacyPhaseToDuplex(
  phase: 'idle' | 'listening' | 'thinking' | 'speaking',
  opts?: { followupActive?: boolean; privacyMuted?: boolean; alerting?: boolean },
): DuplexConversationPhase {
  if (opts?.privacyMuted) {
    return 'privacy_muted';
  }
  if (opts?.alerting) {
    return 'alerting';
  }
  if (phase === 'thinking') {
    return 'thinking';
  }
  if (phase === 'speaking') {
    return 'speaking';
  }
  if (phase === 'listening') {
    return opts?.followupActive ? 'followup_ready' : 'wake_listening';
  }
  if (opts?.followupActive) {
    return 'followup_ready';
  }
  return 'idle';
}

/** Duck TTS gain during barge-in (best-effort duplex until AEC evidence exists). */
export function bargeInDuckGain(active: boolean): number {
  return active ? 0.15 : 1;
}

export function shouldRejectSpeakerBleed(input: {
  transcript: string;
  lastSpokenReply: string;
  similarityThreshold?: number;
}): boolean {
  const spoken = normalize(input.lastSpokenReply);
  const heard = normalize(input.transcript);
  if (!spoken || !heard || heard.length < 8) {
    return false;
  }
  if (spoken.includes(heard) || heard.includes(spoken.slice(0, Math.min(40, spoken.length)))) {
    return true;
  }
  const threshold = input.similarityThreshold ?? 0.72;
  return jaccardTokens(spoken, heard) >= threshold;
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function jaccardTokens(a: string, b: string): number {
  const left = new Set(a.split(' ').filter(Boolean));
  const right = new Set(b.split(' ').filter(Boolean));
  if (!left.size || !right.size) {
    return 0;
  }
  let inter = 0;
  for (const token of left) {
    if (right.has(token)) {
      inter += 1;
    }
  }
  const union = left.size + right.size - inter;
  return union === 0 ? 0 : inter / union;
}
