import { describe, expect, it } from 'vitest';

import {
  clearKairoVoicePlaybackActive,
  kairoVoiceActiveEngine,
  kairoVoiceActiveReason,
  kairoVoiceEngineBadge,
  kairoVoiceLastEngine,
  kairoVoiceLastReason,
  markKairoVoicePlaybackActive,
  recordKairoVoicePlayback,
  resetKairoVoiceDiagnostics,
} from './kairo-voice-diagnostics';

describe('kairo voice diagnostics', () => {
  it('shows azure badge while playback is active', () => {
    resetKairoVoiceDiagnostics();
    markKairoVoicePlaybackActive('azure', 'first_byte_ms=42');
    expect(kairoVoiceEngineBadge()).toBe('Azure voice');
    clearKairoVoicePlaybackActive();
    expect(kairoVoiceEngineBadge()).toBe('');
  });

  it('shows browser badge with fallback reason during playback', () => {
    resetKairoVoiceDiagnostics();
    markKairoVoicePlaybackActive('browser', 'azure_unavailable');
    expect(kairoVoiceEngineBadge()).toBe('Browser voice · azure_unavailable');
  });

  it('falls back to last engine receipt after playback finishes', () => {
    resetKairoVoiceDiagnostics();
    recordKairoVoicePlayback({ engine: 'azure', reason: 'first_byte_ms=18' }, 'Systems nominal.');
    expect(kairoVoiceActiveEngine.value).toBeNull();
    expect(kairoVoiceLastEngine.value).toBe('azure');
    expect(kairoVoiceEngineBadge()).toBe('Azure voice');
  });

  it('keeps browser fallback reason on last receipt', () => {
    resetKairoVoiceDiagnostics();
    recordKairoVoicePlayback({ engine: 'browser', reason: 'synthesis_failed' }, 'Hello');
    expect(kairoVoiceEngineBadge()).toBe('Browser voice · synthesis_failed');
    expect(kairoVoiceLastReason.value).toBe('synthesis_failed');
  });
});
