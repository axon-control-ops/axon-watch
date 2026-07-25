import { describe, expect, it } from 'vitest';

import {
  briefingAttentionStatusLabel,
  resolveKairoBriefingAttention,
  shouldShowBriefingAttentionInCommandMode,
} from './kairo-briefing-attention';

describe('kairo-briefing-attention', () => {
  it('flags approvals as highest-priority briefing attention', () => {
    const attention = resolveKairoBriefingAttention({
      pendingApprovals: 1,
      criticalSignals: 2,
      highSignals: 3,
      degraded: true,
      briefingLoaded: true,
    });

    expect(attention.active).toBe(true);
    expect(attention.severity).toBe('high');
    expect(attention.message).toBe('1 approval needs review');
    expect(attention.badgeCount).toBe(1);
  });

  it('surfaces degraded runtime when no approvals or signals remain', () => {
    const attention = resolveKairoBriefingAttention({
      pendingApprovals: 0,
      criticalSignals: 0,
      highSignals: 0,
      degraded: true,
      briefingLoaded: true,
    });

    expect(attention.active).toBe(true);
    expect(attention.message).toContain('degraded');
  });

  it('only shows command-mode attention cues while command hero is active', () => {
    const attention = resolveKairoBriefingAttention({
      pendingApprovals: 1,
      criticalSignals: 0,
      highSignals: 0,
      degraded: false,
      briefingLoaded: true,
    });

    expect(shouldShowBriefingAttentionInCommandMode('command', attention)).toBe(true);
    expect(shouldShowBriefingAttentionInCommandMode('briefing', attention)).toBe(false);
    expect(briefingAttentionStatusLabel(attention)).toBe('VAXON · 1 approval needs review');
  });
});
