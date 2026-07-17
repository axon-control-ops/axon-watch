import { describe, expect, it } from 'vitest';

import {
  AGENT_DOCK_WIDTH_STEP_LARGE_PX,
  AGENT_DOCK_WIDTH_STEP_PX,
  applyAgentDockResizeKeyAction,
  clampAgentDockWidth,
  defaultAgentDockWidth,
  maxAgentDockWidth,
  MAX_AGENT_DOCK_WIDTH,
  MIN_AGENT_DOCK_WIDTH,
  nudgeAgentDockWidth,
  resolveAgentDockResizeKey,
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

  it('exposes a viewport-aware maximum for separator aria values', () => {
    expect(maxAgentDockWidth(1440)).toBe(MAX_AGENT_DOCK_WIDTH);
    expect(maxAgentDockWidth(800)).toBe(320);
  });

  it('nudges dock width with keyboard step sizes and clamps', () => {
    expect(nudgeAgentDockWidth(400, AGENT_DOCK_WIDTH_STEP_PX, 1440)).toBe(416);
    expect(nudgeAgentDockWidth(400, -AGENT_DOCK_WIDTH_STEP_LARGE_PX, 1440)).toBe(352);
    expect(nudgeAgentDockWidth(MIN_AGENT_DOCK_WIDTH, -AGENT_DOCK_WIDTH_STEP_PX, 1440)).toBe(
      MIN_AGENT_DOCK_WIDTH,
    );
    expect(nudgeAgentDockWidth(MAX_AGENT_DOCK_WIDTH, AGENT_DOCK_WIDTH_STEP_PX, 1440)).toBe(
      MAX_AGENT_DOCK_WIDTH,
    );
  });

  it('maps resize separator keys to width actions', () => {
    expect(resolveAgentDockResizeKey('ArrowLeft', false)).toEqual({
      type: 'nudge',
      delta: AGENT_DOCK_WIDTH_STEP_PX,
    });
    expect(resolveAgentDockResizeKey('ArrowRight', true)).toEqual({
      type: 'nudge',
      delta: -AGENT_DOCK_WIDTH_STEP_LARGE_PX,
    });
    expect(resolveAgentDockResizeKey('Home', false)).toEqual({ type: 'min' });
    expect(resolveAgentDockResizeKey('End', false)).toEqual({ type: 'max' });
    expect(resolveAgentDockResizeKey('Enter', false)).toEqual({ type: 'reset' });
    expect(resolveAgentDockResizeKey('Escape', false)).toBeNull();
  });

  it('applies keyboard resize actions inside viewport bounds', () => {
    expect(
      applyAgentDockResizeKeyAction(400, { type: 'nudge', delta: AGENT_DOCK_WIDTH_STEP_PX }, 1440),
    ).toBe(416);
    expect(applyAgentDockResizeKeyAction(400, { type: 'min' }, 1440)).toBe(MIN_AGENT_DOCK_WIDTH);
    expect(applyAgentDockResizeKeyAction(400, { type: 'max' }, 1440)).toBe(MAX_AGENT_DOCK_WIDTH);
    expect(applyAgentDockResizeKeyAction(400, { type: 'reset' }, 1440)).toBe(
      defaultAgentDockWidth(1440),
    );
  });
});
