import { describe, expect, it, vi, afterEach } from 'vitest';

import {
  resetKairoAudioUnlockState,
  unlockKairoAudioPlayback,
} from '../../lib/kairo-audio-unlock';
import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { deliverSpokenOperatorAlert, registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

import { handleVoiceDeckSpokenAlert, registerVoiceDeckOnBoot } from './voice-deck';

vi.mock('../../lib/kairo-voice-playback', () => ({
  speakKairoLine: vi.fn(),
}));

async function unlockMediaForTests(): Promise<void> {
  class FakeAudioContext {
    state = 'running';
    resume = vi.fn(async () => undefined);
    createBuffer = vi.fn(() => ({}));
    createBufferSource = vi.fn(() => ({
      buffer: null as unknown,
      connect: vi.fn(),
      start: vi.fn(),
    }));
    destination = {};
    close = vi.fn(async () => undefined);
  }
  class FakeAudio {
    volume = 1;
    src = '';
    setAttribute = vi.fn();
    play = vi.fn(async () => undefined);
    pause = vi.fn();
    constructor(src: string) {
      this.src = src;
    }
  }
  vi.stubGlobal('AudioContext', FakeAudioContext);
  vi.stubGlobal('Audio', FakeAudio);
  await unlockKairoAudioPlayback();
}

describe('voice deck', () => {
  afterEach(() => {
    registerVoiceDeckSpokenAlertHandler(null);
    resetKairoAudioUnlockState();
    vi.mocked(speakKairoLine).mockReset();
    vi.unstubAllGlobals();
  });

  it('speaks eligible alerts through the deck handler', async () => {
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });

    const handled = await handleVoiceDeckSpokenAlert({
      eligible: true,
      reason: 'operator_approval_required',
      signal_id: 'signal_1',
      message: 'VAXON: 1 approval waiting for your review.',
    });

    expect(handled).toBe(true);
    expect(speakKairoLine).toHaveBeenCalledOnce();
    expect(speakKairoLine).toHaveBeenCalledWith(
      'VAXON: 1 approval waiting for your review.',
      expect.objectContaining({
        priority: 'alert',
        speaker: expect.objectContaining({ kind: 'vaxon', id: 'vaxon' }),
      }),
    );
  });

  it('declines ineligible alerts without speaking', async () => {
    const handled = await handleVoiceDeckSpokenAlert({
      eligible: false,
      reason: 'spoken_alerts_disabled',
      signal_id: null,
      message: '',
    });

    expect(handled).toBe(false);
    expect(speakKairoLine).not.toHaveBeenCalled();
  });

  it('registers boot handler that routes spoken alerts to voice deck channel', async () => {
    await unlockMediaForTests();
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    registerVoiceDeckOnBoot();

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: Watch summary degraded.',
      },
      storage,
    );

    expect(channel).toBe('voice_deck');
    expect(speakKairoLine).toHaveBeenCalledOnce();
  });
});
