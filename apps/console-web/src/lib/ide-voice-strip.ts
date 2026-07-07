import type { OperatorPresenceSettings } from '../contracts/canonical';

export function shouldShowIdeVoiceStrip(input: {
  layoutMode: 'operator' | 'ide';
  settings: Pick<OperatorPresenceSettings, 'ide_voice_strip_enabled'>;
  foundationSurface: boolean;
}): boolean {
  if (input.foundationSurface || input.layoutMode !== 'ide') {
    return false;
  }
  return Boolean(input.settings.ide_voice_strip_enabled);
}

export function ideVoiceSpeechAllowed(input: {
  layoutMode: 'operator' | 'ide';
  settings: Pick<OperatorPresenceSettings, 'ide_voice_strip_enabled' | 'privacy_mode'>;
}): boolean {
  if (input.settings.privacy_mode) {
    return false;
  }
  if (input.layoutMode !== 'ide') {
    return true;
  }
  return Boolean(input.settings.ide_voice_strip_enabled);
}

export function ideVoiceStripStatusLabel(input: {
  speaking: boolean;
  narration: OperatorPresenceSettings['kairo_narration'];
  liveLine: string | null;
}): string {
  if (input.speaking) {
    return 'Speaking…';
  }
  if (input.liveLine?.trim()) {
    return input.liveLine.trim();
  }
  if (input.narration === 'off') {
    return 'Voice strip on — narration off';
  }
  return 'Voice strip ready';
}
