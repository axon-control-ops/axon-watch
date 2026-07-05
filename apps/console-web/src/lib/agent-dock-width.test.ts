import { describe, expect, it } from 'vitest';

import {
  clampAgentDockWidth,
  defaultAgentDockWidth,
  MAX_AGENT_DOCK_WIDTH,
  MIN_AGENT_DOCK_WIDTH,
} from './agent-dock-width';

describe('agent dock width', () => {
  it('clamps dock width inside viewport-safe bounds', () => {
    expect(clampAgentDockWidth(120, 1440)).toBe(MIN_AGENT_DOCK_WIDTH);
    expect(clampAgentDockWidth(1200, 1440)).toBe(MAX_AGENT_DOCK_WIDTH);
    expect(clampAgentDockWidth(420, 1440)).toBe(420);
  });

  it('picks a viewport-aware default width', () => {
    expect(defaultAgentDockWidth(1440)).toBe(461);
    expect(defaultAgentDockWidth(1024)).toBe(328);
  });
});
