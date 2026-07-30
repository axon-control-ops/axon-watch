import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  clearQueuedSpokenAlerts,
  deliverSpokenOperatorAlert,
  flushQueuedSpokenAlerts,
  pendingSpokenAlertQueueSize,
  registerVoiceDeckSpokenAlertHandler,
} from './spoken-alert-delivery';
import {
  resetKairoAudioUnlockState,
  unlockKairoAudioPlayback,
} from './kairo-audio-unlock';
import { clearKairoVoiceFollowupWindow } from './kairo-voice-followup-window';
import { speakKairoLine } from './kairo-voice-playback';
import * as followup from './kairo-voice-followup-window';

vi.mock('./kairo-voice-playback', () => ({
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

describe('spoken alert delivery', () => {
  afterEach(() => {
    registerVoiceDeckSpokenAlertHandler(null);
    clearQueuedSpokenAlerts();
    clearKairoVoiceFollowupWindow();
    resetKairoAudioUnlockState();
    vi.mocked(speakKairoLine).mockReset();
    vi.unstubAllGlobals();
  });

  it('queues alerts until media unlock instead of speaking early', async () => {
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: critical.',
      },
      storage,
    );
    expect(channel).toBe('queued');
    expect(pendingSpokenAlertQueueSize()).toBe(1);
    expect(speakKairoLine).not.toHaveBeenCalled();
  });

  it('flushes queued alerts after unlock and opens follow-up window', async () => {
    const scheduleSpy = vi.spyOn(followup, 'scheduleKairoVoiceFollowupWindowAfterSpeech');
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };
    await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'high_urgency_signal',
        signal_id: 'signal_x',
        message: 'VAXON attention: critical.',
      },
      storage,
    );
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });
    await unlockMediaForTests();
    await flushQueuedSpokenAlerts();
    expect(speakKairoLine).toHaveBeenCalledOnce();
    expect(pendingSpokenAlertQueueSize()).toBe(0);
    expect(scheduleSpy).toHaveBeenCalled();
    scheduleSpy.mockRestore();
  });

  it('uses voice deck hook when registered and handler accepts', async () => {
    await unlockMediaForTests();
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
    await unlockMediaForTests();
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
    expect(speakKairoLine).toHaveBeenCalledWith(
      'VAXON attention: Watch summary degraded.',
      expect.objectContaining({
        priority: 'alert',
        speaker: expect.objectContaining({ kind: 'vaxon', id: 'vaxon' }),
      }),
    );
  });

  it('bypasses voice deck for direct theater playback and keeps MC Azure defaults', async () => {
    await unlockMediaForTests();
    const handler = vi.fn().mockResolvedValue(true);
    registerVoiceDeckSpokenAlertHandler(handler);
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'azure', reason: null });
    const onPlaybackStart = vi.fn();
    const storage = {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
    };

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'report_theater_turn',
        signal_id: null,
        message: 'Mira here. Lead reports complete.',
      },
      storage,
      {
        priority: 'alert',
        dedupe: false,
        queueUntilUnlock: false,
        openFollowupWindow: false,
        directPlayback: true,
        allowDuringReportTheater: true,
        azureVoiceId: 'en-US-JennyNeural',
        speaker: {
          kind: 'employee',
          id: 'emp_mira',
          name: 'Mira',
          roleLabel: 'Lead',
          azureVoiceId: 'en-US-JennyNeural',
        },
        onPlaybackStart,
      },
    );

    expect(channel).toBe('azure');
    expect(handler).not.toHaveBeenCalled();
    expect(speakKairoLine).toHaveBeenCalledWith(
      'Mira here. Lead reports complete.',
      expect.objectContaining({
        priority: 'alert',
        allowDuringReportTheater: true,
        azureVoiceId: 'en-US-JennyNeural',
        onPlaybackStart,
        ttsTimeoutMs: undefined,
      }),
    );
  });

  it('reports browser fallback channel', async () => {
    await unlockMediaForTests();
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

  it('can bypass dedupe for explicit replay requests', async () => {
    await unlockMediaForTests();
    vi.mocked(speakKairoLine).mockResolvedValue({ engine: 'browser', reason: 'preferred_browser' });
    const storage = {
      getItem: vi.fn().mockReturnValue('operator_briefing_spoken'),
      setItem: vi.fn(),
    };

    const channel = await deliverSpokenOperatorAlert(
      {
        eligible: true,
        reason: 'operator_briefing_spoken',
        signal_id: null,
        message: 'Watch bootstrap is ready for your review, sir.',
      },
      storage,
      { dedupe: false },
    );

    expect(channel).toBe('browser');
    expect(speakKairoLine).toHaveBeenCalledOnce();
  });
});
