import { describe, expect, it } from 'vitest';

import {
  galaxyOrbBeads,
  galaxyOrbHint,
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
    expect(ticks).toHaveLength(48);
    expect(ticks.some((tick) => tick.major)).toBe(true);
  });

  it('places five beads on the dial', () => {
    expect(galaxyOrbBeads()).toHaveLength(5);
  });

  it('maps presence to orb classes', () => {
    expect(galaxyOrbStateClass('alerting', false)).toContain('alerting');
    expect(galaxyOrbStateClass('observing', true)).toContain('speaking');
    expect(galaxyOrbStateClass('idle', false, 'thinking')).toContain('busy');
    expect(galaxyOrbModeClass(true)).toContain('hands-free');
    expect(galaxyOrbModeClass(false)).toContain('manual');
  });

  it('shows busy status while thinking', () => {
    expect(galaxyOrbStatusLabel('thinking', false)).toBe('BUSY');
    expect(galaxyOrbModeLabel(true, 'thinking')).toBe('Checking…');
    expect(galaxyOrbHint('idle', false, 'thinking', true)).toContain('checking');
  });

  it('describes hands-free in orb hints', () => {
    expect(galaxyOrbHint('observing', false, 'idle', true)).toBe('Say "VAXON" for commands');
    expect(galaxyOrbModeLabel(true, 'idle')).toBe('');
  });

  it('shortens model labels', () => {
    expect(galaxyOrbModelLabel('gpt-4o')).toBe('GPT-4O');
    expect(galaxyOrbModelLabel('claude-opus-4-8-thinking-high')).toContain('…');
  });
});
