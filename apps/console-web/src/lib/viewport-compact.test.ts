import { describe, expect, it } from 'vitest';

import type { OperatorPresence } from '../contracts/canonical';

import {
  MOBILE_COMPACT_BREAKPOINT,
  shouldRequestViewportCompactBriefing,
  shouldUseMobileCompactLayout,
} from './viewport-compact';

const presence: OperatorPresence = {
  persona_voice_line: 'KAIRO: ready',
  presence_state: 'observing' as const,
  settings: {
    operator_persona_enabled: true,
    spoken_alerts_enabled: true,
    privacy_mode: false,
    mobile_compact_preferred: true,
    kairo_narration: 'conversational' as const,
    ide_voice_strip_enabled: false,
    hands_free_enabled: false,
    speech_rate: 1.0,
    speech_pitch: 1.04,
    azure_voice_id: 'en-GB-RyanNeural',
    stt_mode: 'browser' as const,
    voice_routing_mode: 'template_first' as const,
    narrate_tool_progress: false,
    proactive_duplex_enabled: false,
    autonomy_mode: 'manual',
    vaxon_model_id: 'gpt-5.4-high',
    auto_composer_runtime_override_enabled: false,
    auto_composer_runtime_target: '',
  },
  spoken_alert: {
    eligible: false,
    reason: 'no_interruptive_signal',
    signal_id: null,
    message: '',
  },
  mobile: { compact_layout: false, foreground_only: true },
};

describe('viewport compact helpers', () => {
  it('requests compact briefing below the breakpoint', () => {
    expect(shouldRequestViewportCompactBriefing(767, presence)).toBe(true);
    expect(shouldRequestViewportCompactBriefing(768, presence)).toBe(false);
  });

  it('uses server compact_layout flag immediately', () => {
    expect(
      shouldUseMobileCompactLayout(1200, {
        ...presence,
        mobile: { compact_layout: true, foreground_only: true },
      }),
    ).toBe(true);
  });

  it('reacts to viewport width without server flag', () => {
    expect(shouldUseMobileCompactLayout(640, presence)).toBe(true);
    expect(shouldUseMobileCompactLayout(1024, presence)).toBe(false);
  });

  it('respects disabled mobile compact preference', () => {
    expect(
      shouldRequestViewportCompactBriefing(640, presence, {
        ...presence.settings,
        mobile_compact_preferred: false,
      }),
    ).toBe(false);
  });

  it('documents the locked breakpoint', () => {
    expect(MOBILE_COMPACT_BREAKPOINT).toBe(768);
  });
});
