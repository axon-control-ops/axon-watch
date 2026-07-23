import { describe, expect, it, beforeEach } from 'vitest';

import {
  clearVoiceLoopDiagnostics,
  listVoiceLoopDiagnostics,
  recordVoiceLoopDiagnostic,
  summarizeVoiceLoopDiagnostics,
} from './kairo-voice-loop-diagnostics';

describe('kairo-voice-loop-diagnostics', () => {
  beforeEach(() => {
    clearVoiceLoopDiagnostics();
  });

  it('records bounded events without growing forever', () => {
    for (let i = 0; i < 120; i += 1) {
      recordVoiceLoopDiagnostic({ kind: 'hands_free_decision', action: 'hold', reason: String(i) });
    }
    expect(listVoiceLoopDiagnostics()).toHaveLength(80);
    expect(summarizeVoiceLoopDiagnostics().count).toBe(80);
  });

  it('summarizes timeouts and errors', () => {
    recordVoiceLoopDiagnostic({ kind: 'converse_timeout', latencyMs: 20000 });
    recordVoiceLoopDiagnostic({ kind: 'converse_error', reason: 'boom' });
    const summary = summarizeVoiceLoopDiagnostics();
    expect(summary.timeoutCount).toBe(1);
    expect(summary.errorCount).toBe(1);
    expect(summary.lastKind).toBe('converse_error');
  });
});
