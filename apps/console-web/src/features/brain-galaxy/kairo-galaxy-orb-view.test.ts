import { describe, expect, it } from 'vitest';

import {
  galaxyOrbBeads,
  galaxyOrbGlassShards,
  galaxyOrbHint,
  galaxyOrbMeshDots,
  galaxyOrbModeClass,
  galaxyOrbModeLabel,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbStatusLabel,
  galaxyOrbTicks,
} from './kairo-galaxy-orb-view';

describe('kairo-galaxy-orb-view', () => {
  it('builds tick marks around the orb', () => {
    const ticks = galaxyOrbTicks();
    expect(ticks).toHaveLength(72);
    expect(ticks.some((tick) => tick.major)).toBe(true);
  });

  it('places five beads on the dial', () => {
    expect(galaxyOrbBeads()).toHaveLength(5);
  });

  it('builds denser mesh with pink accents and glass shards', () => {
    const mesh = galaxyOrbMeshDots();
    expect(mesh.length).toBeGreaterThan(64);
    expect(mesh.some((dot) => dot.accent === 'pink')).toBe(true);
    const shards = galaxyOrbGlassShards();
    expect(shards).toHaveLength(12);
    expect(shards[0]?.points.split(' ').length).toBe(4);
  });

  it('maps presence to orb classes', () => {
    expect(galaxyOrbStateClass('alerting', false)).toContain('alerting');
    expect(galaxyOrbStateClass('observing', true)).toContain('speaking');
    expect(galaxyOrbStateClass('idle', false, 'thinking')).toContain('busy');
    expect(galaxyOrbStateClass('observing', false, 'idle')).toContain('standby');
    expect(galaxyOrbStateClass('observing', false, 'idle')).not.toContain('listening');
    expect(galaxyOrbStateClass('observing', false, 'idle', false, true)).toContain('autonomous');
    expect(galaxyOrbModeClass(true)).toContain('hands-free');
    expect(galaxyOrbModeClass(false)).toContain('manual');
  });

  it('shows busy status while thinking', () => {
    expect(galaxyOrbStatusLabel('thinking', false)).toBe('BUSY');
    expect(galaxyOrbModeLabel(true, 'thinking')).toBe('Checking…');
    expect(galaxyOrbHint('idle', false, 'thinking', true)).toContain('checking');
  });

  it('describes hands-free in orb hints', () => {
    expect(galaxyOrbHint('observing', false, 'idle', true)).toContain('Say "VAXON" for commands');
    expect(galaxyOrbModeLabel(true, 'idle')).toBe('Hands-free');
  });

  it('surfaces wake-word gate feedback on the orb hint', () => {
    expect(
      galaxyOrbHint(
        'observing',
        false,
        'idle',
        true,
        'Heard “hello” — say “VAXON” first',
      ),
    ).toBe('Heard “hello” — say “VAXON” first');
  });

  it('only labels LISTENING when a mic session is open', () => {
    expect(galaxyOrbStatusLabel('idle', false, false)).toBe('READY');
    expect(galaxyOrbStatusLabel('listening', false, true)).toBe('LISTENING');
  });

  it('shortens model labels', () => {
    expect(galaxyOrbModelLabel('gpt-4o')).toBe('GPT-4O');
    expect(galaxyOrbModelLabel('claude-opus-4-8-thinking-high')).toContain('…');
  });
});
