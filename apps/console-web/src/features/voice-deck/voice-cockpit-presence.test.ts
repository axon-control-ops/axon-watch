import { describe, expect, it } from 'vitest';

import {
  shouldReactToBriefingSpokenAlert,
  voiceCockpitStatusLine,
} from './voice-cockpit-presence';

describe('voice cockpit presence', () => {
  it('builds a status line from operator presence', () => {
    expect(
      voiceCockpitStatusLine({
        persona_voice_line: 'KAIRO: 1 approval waiting.',
        presence_state: 'alerting',
        settings: {
          operator_persona_enabled: true,
          spoken_alerts_enabled: true,
          privacy_mode: false,
          mobile_compact_preferred: true,
          kairo_narration: 'conversational',
          ide_voice_strip_enabled: false,
          hands_free_enabled: false,
          speech_rate: 1.0,
          speech_pitch: 1.04,
          azure_voice_id: 'en-GB-RyanNeural',
          stt_mode: 'browser',
          voice_routing_mode: 'template_first',
          narrate_tool_progress: false,
          proactive_duplex_enabled: false,
        },
        spoken_alert: {
          eligible: true,
          reason: 'operator_approval_required',
          signal_id: null,
          message: 'KAIRO: 1 approval waiting.',
        },
        mobile: { compact_layout: true, foreground_only: true },
      }),
    ).toContain('approval');
  });

  it('detects eligible briefing spoken alerts', () => {
    expect(
      shouldReactToBriefingSpokenAlert({
        eligible: true,
        reason: 'operator_approval_required',
        signal_id: null,
        message: 'KAIRO attention required.',
      }),
    ).toBe(true);
    expect(
      shouldReactToBriefingSpokenAlert({
        eligible: false,
        reason: 'no_interruptive_signal',
        signal_id: null,
        message: '',
      }),
    ).toBe(false);
  });
});
