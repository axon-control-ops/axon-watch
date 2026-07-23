import { describe, expect, it } from 'vitest';

import {
  selectDefaultWakeWordEngineId,
  WAKE_WORD_ENGINE_BENCHMARKS,
} from './wake-word-engine';

describe('wake-word-engine', () => {
  it('defaults to the interim open engine without a proprietary key', () => {
    expect(selectDefaultWakeWordEngineId()).toBe('browser-energy-gate');
    expect(WAKE_WORD_ENGINE_BENCHMARKS.some((row) => row.engineId === 'porcupine')).toBe(true);
    const porcupine = WAKE_WORD_ENGINE_BENCHMARKS.find((row) => row.engineId === 'porcupine');
    expect(porcupine?.license.toLowerCase()).toContain('proprietary');
  });
});
