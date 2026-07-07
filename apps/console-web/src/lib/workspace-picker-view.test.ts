import { describe, expect, it } from 'vitest';

import type { WorkspaceRecord } from '../contracts/canonical';

import {
  shortenWorkspacePath,
  workspacePickerMetaLabel,
  workspacePickerPrimaryLabel,
} from './workspace-picker-view';

describe('workspace picker view', () => {
  it('uses display name as the primary label', () => {
    const workspace: WorkspaceRecord = {
      workspace_id: 'workspace_axon_watch',
      display_name: 'Axon Watch',
      project_root: '/home/edp/axon-nvme/repos/axon-watch',
    };

    expect(workspacePickerPrimaryLabel(workspace)).toBe('Axon Watch');
  });

  it('prefers project root for the meta label', () => {
    const workspace: WorkspaceRecord = {
      workspace_id: 'workspace_axon_watch',
      display_name: 'Axon Watch',
      project_root: '/home/edp/axon-nvme/repos/axon-watch',
    };

    expect(workspacePickerMetaLabel(workspace)).toBe('/…/repos/axon-watch');
  });

  it('falls back to workspace id when no project root exists', () => {
    const workspace: WorkspaceRecord = {
      workspace_id: 'workspace_axon_local',
      display_name: 'Axon Local',
    };

    expect(workspacePickerMetaLabel(workspace)).toBe('workspace_axon_local');
  });

  it('shortens deep paths to the last two segments', () => {
    expect(shortenWorkspacePath('/home/edp/axon-nvme/repos/axon-watch')).toBe(
      '/…/repos/axon-watch',
    );
  });
});
