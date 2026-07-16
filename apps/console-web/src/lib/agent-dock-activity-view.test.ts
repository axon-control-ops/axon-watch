import { describe, expect, it } from 'vitest';

import {
  buildIdeComposerActivityLabel,
  buildIdeStreamActivityLabel,
} from './agent-dock-activity-view';

describe('agent-dock-activity-view', () => {
  it('labels full access agent work distinctly', () => {
    expect(buildIdeComposerActivityLabel('agent', 'full')).toContain('Full Access');
    expect(buildIdeComposerActivityLabel('agent', 'consultative')).not.toContain('Full Access');
  });

  it('labels debug mode distinctly from agent', () => {
    expect(buildIdeComposerActivityLabel('debug', 'full')).toContain('Debug');
    expect(buildIdeComposerActivityLabel('debug', 'full')).toContain('Full Access');
    expect(buildIdeComposerActivityLabel('debug', 'consultative')).toMatch(/^Debug/);
    expect(buildIdeComposerActivityLabel('debug', 'consultative')).not.toContain('Full Access');
  });

  it('labels streaming for full access', () => {
    expect(buildIdeStreamActivityLabel('full')).toContain('Full Access');
    expect(buildIdeStreamActivityLabel('full', 'agent')).toContain('Full Access');
  });

  it('keeps streaming labels mode-aware', () => {
    expect(buildIdeStreamActivityLabel('consultative', 'plan')).toBe('Plan — streaming outline…');
    expect(buildIdeStreamActivityLabel('consultative', 'ask')).toBe('Ask — streaming reply…');
    expect(buildIdeStreamActivityLabel('full', 'debug')).toContain('Debug · Full Access');
    expect(buildIdeStreamActivityLabel('consultative', 'agent')).toBe(
      'Agent — streaming runtime output…',
    );
  });
});
