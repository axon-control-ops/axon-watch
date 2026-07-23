import { describe, expect, it } from 'vitest';

import { resolveGalaxyPresence } from './galaxy-presence-state';

const base = {
  selectedNodeId: null as string | null,
  selectedNodeKind: null as string | null,
  conversationPhase: 'idle' as const,
  speechCapturing: false,
  kairoSpeechActive: false,
  agentStreamActive: false,
  pendingApprovals: 0,
  criticalSignals: 0,
  highSignals: 0,
};

describe('resolveGalaxyPresence', () => {
  it('defaults to idle', () => {
    const resolved = resolveGalaxyPresence(base);
    expect(resolved.phase).toBe('idle');
    expect(resolved.coreOrbMode).toBe('idle');
    expect(resolved.busy).toBe(false);
  });

  it('prefers autonomous over speaking', () => {
    const resolved = resolveGalaxyPresence({
      ...base,
      agentStreamActive: true,
      kairoSpeechActive: true,
      conversationPhase: 'speaking',
    });
    expect(resolved.phase).toBe('autonomous');
    expect(resolved.coreOrbMode).toBe('autonomous');
    expect(resolved.busy).toBe(true);
  });

  it('prefers speaking over listening', () => {
    const resolved = resolveGalaxyPresence({
      ...base,
      kairoSpeechActive: true,
      speechCapturing: true,
    });
    expect(resolved.phase).toBe('speaking');
  });

  it('maps listening from manual PTT phase only — not ambient speechCapturing', () => {
    expect(resolveGalaxyPresence({ ...base, speechCapturing: true }).phase).toBe('idle');
    expect(
      resolveGalaxyPresence({
        ...base,
        speechCapturing: true,
        criticalSignals: 1,
      }).phase,
    ).toBe('alerting');
    expect(
      resolveGalaxyPresence({ ...base, conversationPhase: 'listening' }).phase,
    ).toBe('listening');
    expect(
      resolveGalaxyPresence({ ...base, conversationPhase: 'listening' }).presenceAmp,
    ).toBe(0.55);
    expect(
      resolveGalaxyPresence({ ...base, conversationPhase: 'thinking' }).phase,
    ).toBe('thinking');
    expect(
      resolveGalaxyPresence({ ...base, conversationPhase: 'thinking' }).presenceAmp,
    ).toBe(1);
  });

  it('maps alerting below conversation activity', () => {
    expect(
      resolveGalaxyPresence({ ...base, pendingApprovals: 1 }).phase,
    ).toBe('alerting');
    expect(
      resolveGalaxyPresence({ ...base, pendingApprovals: 1 }).presenceAmp,
    ).toBe(0.55);
    expect(
      resolveGalaxyPresence({
        ...base,
        pendingApprovals: 1,
        conversationPhase: 'thinking',
      }).phase,
    ).toBe('thinking');
  });

  it('keeps ambient energy while idle', () => {
    expect(resolveGalaxyPresence(base).presenceAmp).toBe(0.32);
  });

  it('maps workspace selection when idle', () => {
    const resolved = resolveGalaxyPresence({
      ...base,
      selectedNodeId: 'ws-1',
      selectedNodeKind: 'workspace',
    });
    expect(resolved.phase).toBe('workspace_selected');
    expect(resolved.coreOrbMode).toBe('idle');
    expect(resolved.presenceAmp).toBe(0.28);
  });
});
