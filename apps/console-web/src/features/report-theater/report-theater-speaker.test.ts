import { beforeEach, describe, expect, it, vi } from 'vitest';

import { speakReportTheaterTurn } from './report-theater-speaker';

const deliverSpokenOperatorAlert = vi.fn();

vi.mock('../../lib/spoken-alert-delivery', () => ({
  deliverSpokenOperatorAlert: (...args: unknown[]) => deliverSpokenOperatorAlert(...args),
}));

vi.mock('./report-theater-state', () => ({
  setReportTheaterSpeakerName: vi.fn(),
}));

describe('speakReportTheaterTurn', () => {
  beforeEach(() => {
    deliverSpokenOperatorAlert.mockReset().mockResolvedValue('azure');
  });

  it('routes stand-up turns through Mission Control alert delivery without a short Azure timeout', async () => {
    const shell = {
      companyEmployeesForCurrentWorkspace: [
        {
          employee_id: 'emp_mira',
          name: 'Mira',
          role_label: 'Lead',
          azure_voice_id: 'en-US-JennyNeural',
        } as never,
      ],
    };
    const onPlaybackStart = vi.fn();

    await speakReportTheaterTurn(
      shell,
      'Mira here. Lead reports complete.',
      'REPORT',
      'Mira',
      onPlaybackStart,
    );

    expect(deliverSpokenOperatorAlert).toHaveBeenCalledOnce();
    const [, , options] = deliverSpokenOperatorAlert.mock.calls[0]!;
    expect(options).toMatchObject({
      priority: 'alert',
      dedupe: false,
      queueUntilUnlock: false,
      openFollowupWindow: false,
      directPlayback: true,
      allowDuringReportTheater: true,
      azureVoiceId: 'en-US-JennyNeural',
    });
    expect(options.ttsTimeoutMs).toBeUndefined();
    expect(options.speaker).toMatchObject({
      name: 'Mira',
      azureVoiceId: 'en-US-JennyNeural',
    });
  });
});
