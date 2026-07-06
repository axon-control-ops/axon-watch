import { describe, expect, it, vi, afterEach, beforeAll } from 'vitest';

import {
  deliverSpokenOperatorAlert,
  registerVoiceDeckSpokenAlertHandler,
} from './spoken-alert-delivery';
import { resetSpeechQueue } from './speech-queue';

describe('spoken alert delivery', () => {
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

  it('uses voice deck hook when registered and handler accepts', () => {
    const handler = vi.fn().mockReturnValue(true);
    registerVoiceDeckSpokenAlertHandler(handler);
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };

    const channel = deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'operator_approval_required',
        signal_id: null,
        message: 'KAIRO: 1 approval waiting for your review.',
      },
      speech,
      storage,
    );

    expect(channel).toBe('voice_deck');
    expect(handler).toHaveBeenCalledOnce();
    expect(speech.speak).not.toHaveBeenCalled();
  });

  it('falls back to browser TTS when voice deck declines', () => {
    registerVoiceDeckSpokenAlertHandler(vi.fn().mockReturnValue(false));
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };

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

    expect(channel).toBe('browser_tts');
    expect(speech.speak).toHaveBeenCalledOnce();
  });

  it('skips ineligible alerts without invoking handlers', () => {
    const handler = vi.fn();
    registerVoiceDeckSpokenAlertHandler(handler);
    const speech = { speak: vi.fn(), getVoices: vi.fn().mockReturnValue([]) };

    const channel = deliverSpokenOperatorAlert(
      {
        eligible: false,
        reason: 'spoken_alerts_disabled',
        signal_id: null,
        message: '',
      },
      speech,
      {
        getItem: vi.fn(),
        setItem: vi.fn(),
      },
    );

    expect(channel).toBe('skipped');
    expect(handler).not.toHaveBeenCalled();
    expect(speech.speak).not.toHaveBeenCalled();
  });
});
