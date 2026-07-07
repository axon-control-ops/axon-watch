import type { OperatorPresenceSettings } from '../contracts/canonical';

export function ideConversationalVoiceEnabled(
  settings: Pick<OperatorPresenceSettings, 'kairo_narration' | 'privacy_mode'>,
): boolean {
  if (settings.privacy_mode) {
    return false;
  }
  return settings.kairo_narration !== 'off';
}

export function shouldShowIdeVoiceStrip(input: {
  layoutMode: 'operator' | 'ide';
  settings: Pick<OperatorPresenceSettings, 'ide_voice_strip_enabled' | 'kairo_narration' | 'privacy_mode'>;
  foundationSurface: boolean;
  speaking?: boolean;
}): boolean {
  if (input.foundationSurface || input.layoutMode !== 'ide') {
    return false;
  }
  if (input.speaking) {
    return true;
  }
  if (input.settings.ide_voice_strip_enabled) {
    return true;
  }
  return ideConversationalVoiceEnabled(input.settings);
}

export function ideVoiceSpeechAllowed(input: {
  layoutMode: 'operator' | 'ide';
  settings: Pick<
    OperatorPresenceSettings,
    'ide_voice_strip_enabled' | 'kairo_narration' | 'privacy_mode'
  >;
}): boolean {
  if (input.settings.privacy_mode) {
    return false;
  }
  if (input.layoutMode !== 'ide') {
    return true;
  }
  if (input.settings.ide_voice_strip_enabled) {
    return true;
  }
  return ideConversationalVoiceEnabled(input.settings);
}

export function ideVoiceStripStatusLabel(input: {
  speaking: boolean;
  narration: OperatorPresenceSettings['kairo_narration'];
  liveLine: string | null;
  conversationPhase?: 'idle' | 'listening' | 'thinking' | 'speaking';
}): string {
  if (input.speaking || input.conversationPhase === 'speaking') {
    return 'KAIRO speaking — Stop or Esc to interrupt';
  }
  if (input.conversationPhase === 'thinking') {
    return 'KAIRO thinking…';
  }
  if (input.conversationPhase === 'listening') {
    return 'KAIRO listening…';
  }
  if (input.liveLine?.trim()) {
    return input.liveLine.trim();
  }
  if (input.narration === 'off') {
    return 'Voice ready — narration off in settings';
  }
  return 'Ask KAIRO below — spoken replies enabled';
}
