import { describe, expect, it } from 'vitest';

import { workspaceExplorerStatusMessage } from './workspace-explorer-view';

describe('workspaceExplorerStatusMessage', () => {
  it('shows loading and workspace selection copy', () => {
    expect(
      workspaceExplorerStatusMessage({
        loadState: 'loading',
        hasWorkspace: true,
        entryCount: 0,
      }),
    ).toBe('Loading workspace files…');

    expect(
      workspaceExplorerStatusMessage({
        loadState: 'idle',
        hasWorkspace: false,
        entryCount: 0,
      }),
    ).toBe('Select a workspace to browse files.');
  });

  it('shows preparing copy while idle with a workspace selected', () => {
    expect(
      workspaceExplorerStatusMessage({
        loadState: 'idle',
        hasWorkspace: true,
        entryCount: 0,
      }),
    ).toBe('Preparing explorer…');
  });
});
