import { normalizeVoiceTranscript } from './kairo-entity-labels';
import { looksLikeOperatorFollowUp } from './kairo-voice-followup-heuristics';
import { isKairoVoiceFollowupWindowActive } from './kairo-voice-followup-window';
import {
  OPERATOR_PERSONA_WAKE_WORD_RE,
  stripPersonaWakeWordPrefix,
} from './operator-persona-name';

export type KairoVoiceCaptureMode = 'manual' | 'hands_free' | 'barge_in';

export type VoiceGateResult = {
  accept: boolean;
  reason: string;
  submitContent: string | null;
  shouldInterrupt: boolean;
};

const WAKE_WORD_RE = OPERATOR_PERSONA_WAKE_WORD_RE;
const INTERRUPT_RE =
  /\b(stop|interrupt|quiet|cancel|enough|never mind|nevermind|hold on|shut up)\b/i;
const DIRECT_COMMAND_RE =
  /\b(check|run|git|show|open|focus|status|dispatch|handoff|complete|stop run|what'?s|how'?s|tell me)\b/i;

export function hasKairoWakeWord(text: string): boolean {
  return WAKE_WORD_RE.test(normalizeVoiceTranscript(text));
}

export function stripKairoWakeWordPrefix(text: string): string {
  return stripPersonaWakeWordPrefix(normalizeVoiceTranscript(text));
}

export function detectVoiceInterruptPhrase(text: string): boolean {
  const normalized = normalizeVoiceTranscript(text.trim());
  if (!normalized) {
    return false;
  }
  if (INTERRUPT_RE.test(normalized)) {
    return true;
  }
  return hasKairoWakeWord(normalized) && INTERRUPT_RE.test(stripKairoWakeWordPrefix(normalized));
}

function isDirectOperatorCommand(text: string): boolean {
  return DIRECT_COMMAND_RE.test(text);
}

export function evaluateVoiceTranscript(
  transcript: string,
  mode: KairoVoiceCaptureMode,
): VoiceGateResult {
  const normalized = normalizeVoiceTranscript(transcript.trim());
  const rejected = (reason: string): VoiceGateResult => ({
    accept: false,
    reason,
    submitContent: null,
    shouldInterrupt: false,
  });

  if (!normalized) {
    return rejected('empty');
  }

  const interrupt = detectVoiceInterruptPhrase(normalized);
  const wakeWord = hasKairoWakeWord(normalized);
  const stripped = stripKairoWakeWordPrefix(normalized);

  if (mode === 'manual') {
    if (normalized.length < 2) {
      return rejected('too_short');
    }
    return {
      accept: true,
      reason: 'manual',
      submitContent: normalized,
      shouldInterrupt: false,
    };
  }

  if (mode === 'barge_in') {
    if (interrupt) {
      return {
        accept: false,
        reason: 'interrupt',
        submitContent: null,
        shouldInterrupt: true,
      };
    }
    if (wakeWord) {
      const content = stripped || 'hello';
      if (content.length >= 2 || isDirectOperatorCommand(content)) {
        return {
          accept: true,
          reason: 'barge_wake',
          submitContent: content,
          shouldInterrupt: true,
        };
      }
    }
    if (isDirectOperatorCommand(normalized)) {
      return {
        accept: true,
        reason: 'barge_command',
        submitContent: normalized,
        shouldInterrupt: true,
      };
    }
    return rejected('barge_ignored');
  }

  // hands_free — require wake word or explicit operator command; ignore ambient chat.
  if (wakeWord) {
    const content = stripped || 'hello';
    return {
      accept: true,
      reason: 'wake_word',
      submitContent: content,
      shouldInterrupt: false,
    };
  }
  if (isDirectOperatorCommand(normalized)) {
    return {
      accept: true,
      reason: 'direct_command',
      submitContent: normalized,
      shouldInterrupt: false,
    };
  }
  if (isKairoVoiceFollowupWindowActive()) {
    if (looksLikeOperatorFollowUp(normalized)) {
      return {
        accept: true,
        reason: 'follow_up_window',
        submitContent: normalized,
        shouldInterrupt: false,
      };
    }
    return rejected('follow_up_not_recognized');
  }
  if (normalized.length < 10) {
    return rejected('ambient_short');
  }
  return rejected('no_wake_word');
}

const OPERATOR_VISIBLE_GATE_REJECTIONS = new Set([
  'no_wake_word',
  'ambient_short',
  'follow_up_not_recognized',
  'barge_ignored',
  'voice_output_active',
]);

/** Operator-facing copy when hands-free STT hears speech but the gate ignores it. */
export function formatVoiceGateFeedback(
  reason: string | null | undefined,
  heard: string,
  accepted: boolean | null | undefined,
): string | null {
  if (accepted !== false || !reason || !OPERATOR_VISIBLE_GATE_REJECTIONS.has(reason)) {
    return null;
  }
  const snippet = heard.trim().replace(/\s+/g, ' ');
  const clipped =
    snippet.length > 42 ? `${snippet.slice(0, 39).trimEnd()}…` : snippet;

  switch (reason) {
    case 'no_wake_word':
      return clipped
        ? `Heard “${clipped}” — say “VAXON” first`
        : 'Say “VAXON” before the command';
    case 'ambient_short':
      return 'Need “VAXON” + a command';
    case 'follow_up_not_recognized':
      return clipped
        ? `Heard “${clipped}” — clarify, or say “VAXON”`
        : 'Clarify the follow-up, or say “VAXON”';
    case 'barge_ignored':
      return 'Say “VAXON …” or “stop” to barge in';
    case 'voice_output_active':
      return 'VAXON is speaking — say “stop” or wait';
    default:
      return null;
  }
}
