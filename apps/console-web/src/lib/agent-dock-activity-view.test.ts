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

  it('labels streaming for full access', () => {
    expect(buildIdeStreamActivityLabel('full')).toContain('Full Access');
  });
});
