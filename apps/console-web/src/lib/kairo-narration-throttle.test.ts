import { describe, expect, it, vi } from 'vitest';

import {
  createKairoIntervalThrottle,
  createKairoThinkingSpeechThrottle,
  THINKING_SPEECH_INTERVAL_MS,
  TOOL_MILESTONE_INTERVAL_MS,
} from './kairo-narration-throttle';

describe('createKairoThinkingSpeechThrottle', () => {
  it('allows the first line immediately and caps at three per turn', () => {
    const now = vi.fn();
    now.mockReturnValue(0);
    const throttle = createKairoThinkingSpeechThrottle({ now });

    expect(throttle.canSpeak()).toBe(true);
    throttle.recordSpoken();
    expect(throttle.canSpeak()).toBe(false);

    now.mockReturnValue(THINKING_SPEECH_INTERVAL_MS);
    expect(throttle.canSpeak()).toBe(true);
    throttle.recordSpoken();
    now.mockReturnValue(THINKING_SPEECH_INTERVAL_MS * 2);
    throttle.recordSpoken();
    expect(throttle.spokenCount()).toBe(3);
    expect(throttle.canSpeak()).toBe(false);
  });
});

describe('createKairoIntervalThrottle', () => {
  it('enforces a minimum interval between tool milestones', () => {
    const now = vi.fn();
    now.mockReturnValue(0);
    const throttle = createKairoIntervalThrottle({
      intervalMs: TOOL_MILESTONE_INTERVAL_MS,
      now,
    });

    expect(throttle.canSpeak()).toBe(true);
    throttle.recordSpoken();
    expect(throttle.canSpeak()).toBe(false);
    now.mockReturnValue(TOOL_MILESTONE_INTERVAL_MS);
    expect(throttle.canSpeak()).toBe(true);
  });
});
