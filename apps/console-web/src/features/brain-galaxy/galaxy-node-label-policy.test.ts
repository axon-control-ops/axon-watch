import { describe, expect, it } from 'vitest';

import { shouldShowGalaxyNodeLabel } from './galaxy-node-label-policy';

describe('shouldShowGalaxyNodeLabel', () => {
  it('always labels the core', () => {
    expect(
      shouldShowGalaxyNodeLabel({
        node_id: 'core',
        kind: 'core',
        label: 'VAXON CORE',
        tone: 'nominal',
        workspace_id: null,
        detail: '',
      }),
    ).toBe(true);
  });

  it('labels every named workspace including nominal ones', () => {
    expect(
      shouldShowGalaxyNodeLabel({
        node_id: 'ws_dashpro',
        kind: 'workspace',
        label: 'DashPro',
        tone: 'nominal',
        workspace_id: 'workspace_dashpro',
        detail: '',
      }),
    ).toBe(true);
  });

  it('skips workspaces with empty labels', () => {
    expect(
      shouldShowGalaxyNodeLabel({
        node_id: 'ws_empty',
        kind: 'workspace',
        label: '   ',
        tone: 'nominal',
        workspace_id: 'workspace_empty',
        detail: '',
      }),
    ).toBe(false);
  });
});
