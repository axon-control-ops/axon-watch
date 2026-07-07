import { describe, expect, it } from 'vitest';

import {
  galaxyOrbBeads,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
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
  });

  it('shortens model labels', () => {
    expect(galaxyOrbModelLabel('gpt-4o')).toBe('GPT-4O');
    expect(galaxyOrbModelLabel('claude-opus-4-8-thinking-high')).toContain('…');
  });
});
