import { describe, expect, it, vi, afterEach } from 'vitest';

import {
  deliverSpokenOperatorAlert,
  registerVoiceDeckSpokenAlertHandler,
} from './spoken-alert-delivery';
import { speakKairoLine } from './kairo-voice-playback';

vi.mock('./kairo-voice-playback', () => ({
  speakKairoLine: vi.fn(),
}));

describe('spoken alert delivery', () => {
  afterEach(() => {
    registerVoiceDeckSpokenAlertHandler(null);
    vi.mocked(speakKairoLine).mockReset();
  });

  it('uses voice deck hook when registered and handler accepts', async () => {
    const handler = vi.fn().mockResolvedValue(true);
    registerVoiceDeckSpokenAlertHandler(handler);
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'operator_approval_required',
        signal_id: null,
        message: 'VAXON: 1 approval waiting for your review.',
      },
      storage,
    );

    expect(channel).toBe('voice_deck');
    expect(handler).toHaveBeenCalledOnce();
    expect(speakKairoLine).not.toHaveBeenCalled();
  });

  it('uses azure playback when voice deck declines', async () => {
    registerVoiceDeckSpokenAlertHandler(vi.fn().mockResolvedValue(false));
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: Watch summary degraded.',
      },
      storage,
    );

    expect(channel).toBe('azure');
    expect(speakKairoLine).toHaveBeenCalledOnce();
  });

  it('reports browser fallback channel', async () => {
    vi.mocked(speakKairoLine).mockResolvedValue({
      engine: 'browser',
      reason: 'synthesis_failed',
    });
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: Watch summary degraded.',
      },
      storage,
    );

    expect(channel).toBe('browser');
  });

  it('skips ineligible alerts without invoking handlers', async () => {
    const handler = vi.fn();
    registerVoiceDeckSpokenAlertHandler(handler);

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: false,
        reason: 'spoken_alerts_disabled',
        signal_id: null,
        message: '',
      },
      {
        getItem: vi.fn(),
        setItem: vi.fn(),
      },
    );

    expect(channel).toBe('skipped');
    expect(handler).not.toHaveBeenCalled();
    expect(speakKairoLine).not.toHaveBeenCalled();
  });
});
