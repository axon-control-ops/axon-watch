import { describe, expect, it, vi, afterEach } from 'vitest';

import { speakKairoLine } from '../../lib/kairo-voice-playback';
import { deliverSpokenOperatorAlert, registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';

import { handleVoiceDeckSpokenAlert, registerVoiceDeckOnBoot } from './voice-deck';

vi.mock('../../lib/kairo-voice-playback', () => ({
  speakKairoLine: vi.fn(),
}));

describe('voice deck', () => {
  afterEach(() => {
    registerVoiceDeckSpokenAlertHandler(null);
    vi.mocked(speakKairoLine).mockReset();
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
      { priority: 'alert' },
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
