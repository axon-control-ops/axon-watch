/** Per-turn and interval gates for mid-run voice narration (Voice-C). */

export const THINKING_SPEECH_MAX_PER_TURN = 3;
export const THINKING_SPEECH_INTERVAL_MS = 45_000;
export const TOOL_MILESTONE_INTERVAL_MS = 30_000;

export type KairoThinkingSpeechThrottle = {
  reset(): void;
  canSpeak(nowMs?: number): boolean;
  recordSpoken(nowMs?: number): void;
  spokenCount(): number;
};

export function createKairoThinkingSpeechThrottle(input?: {
  maxPerTurn?: number;
  intervalMs?: number;
  now?: () => number;
}): KairoThinkingSpeechThrottle {
  const maxPerTurn = input?.maxPerTurn ?? THINKING_SPEECH_MAX_PER_TURN;
  const intervalMs = input?.intervalMs ?? THINKING_SPEECH_INTERVAL_MS;
  const now = input?.now ?? (() => Date.now());
  let count = 0;
  let lastAt = 0;

  return {
    reset() {
      count = 0;
      lastAt = 0;
    },
    canSpeak(at = now()) {
      if (count >= maxPerTurn) {
        return false;
      }
      if (count === 0) {
        return true;
      }
      return at - lastAt >= intervalMs;
    },
    recordSpoken(at = now()) {
      count += 1;
      lastAt = at;
    },
    spokenCount() {
      return count;
    },
  };
}

export type KairoIntervalThrottle = {
  reset(): void;
  canSpeak(nowMs?: number): boolean;
  recordSpoken(nowMs?: number): void;
};

export function createKairoIntervalThrottle(input: {
  intervalMs: number;
  now?: () => number;
}): KairoIntervalThrottle {
  const now = input.now ?? (() => Date.now());
  let lastAt: number | null = null;

  return {
    reset() {
      lastAt = null;
    },
    canSpeak(at = now()) {
      return lastAt === null || at - lastAt >= input.intervalMs;
    },
    recordSpoken(at = now()) {
      lastAt = at;
    },
  };
}
