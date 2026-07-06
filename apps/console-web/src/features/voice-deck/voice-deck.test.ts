import { describe, expect, it, vi, afterEach, beforeAll } from 'vitest';

import { deliverSpokenOperatorAlert, registerVoiceDeckSpokenAlertHandler } from '../../lib/spoken-alert-delivery';
import { resetSpeechQueue } from '../../lib/speech-queue';

import { handleVoiceDeckSpokenAlert, registerVoiceDeckOnBoot } from './voice-deck';

describe('voice deck', () => {
  beforeAll(() => {
    class MockSpeechSynthesisUtterance {
      message: string;
      rate = 1;

      constructor(message: string) {
        this.message = message;
      }
    }

    vi.stubGlobal('SpeechSynthesisUtterance', MockSpeechSynthesisUtterance);
  });

  afterEach(() => {
    registerVoiceDeckSpokenAlertHandler(null);
    resetSpeechQueue();
  });

  it('speaks eligible alerts through the deck handler', () => {
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };

    const handled = handleVoiceDeckSpokenAlert(
      {
        eligible: true,
        reason: 'operator_approval_required',
        signal_id: 'signal_1',
        message: 'KAIRO: 1 approval waiting for your review.',
      },
      speech,
    );

    expect(handled).toBe(true);
    expect(speech.speak).toHaveBeenCalledOnce();
  });

  it('declines ineligible alerts without speaking', () => {
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };

    const handled = handleVoiceDeckSpokenAlert(
      {
        eligible: false,
        reason: 'spoken_alerts_disabled',
        signal_id: null,
        message: '',
      },
      speech,
    );

    expect(handled).toBe(false);
    expect(speech.speak).not.toHaveBeenCalled();
  });

  it('registers boot handler that routes spoken alerts to voice deck channel', () => {
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    registerVoiceDeckOnBoot(speech);

    const channel = deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'KAIRO attention: Watch summary degraded.',
      },
      speech,
      storage,
    );

    expect(channel).toBe('voice_deck');
    expect(speech.speak).toHaveBeenCalledOnce();
  });
});
