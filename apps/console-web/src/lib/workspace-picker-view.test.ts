import { describe, expect, it } from 'vitest';

import type { WorkspaceRecord } from '../contracts/canonical';

import {
  applyWorkspacePickerAutoState,
  shortenWorkspacePath,
  visibleWorkspacePickerEntries,
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
      workspace_id: 'workspace_tps',
      display_name: 'TPS',
    };

    expect(workspacePickerMetaLabel(workspace)).toBe('workspace_tps');
  });

  it('shortens deep paths to the last two segments', () => {
    expect(shortenWorkspacePath('/home/edp/axon-nvme/repos/axon-watch')).toBe(
      '/…/repos/axon-watch',
    );
  });

  describe('visibleWorkspacePickerEntries', () => {
    const staffed: WorkspaceRecord = { workspace_id: 'workspace_dashpro', has_active_team: true };
    const unstaffed: WorkspaceRecord = {
      workspace_id: 'workspace_bkkinnovationhub',
      has_active_team: false,
    };
    const unknown: WorkspaceRecord = { workspace_id: 'workspace_legacy' }; // has_active_team omitted

    it('hides workspaces with has_active_team explicitly false', () => {
      const result = visibleWorkspacePickerEntries([staffed, unstaffed], null);
      expect(result.map((w) => w.workspace_id)).toEqual(['workspace_dashpro']);
    });

    it('keeps workspaces that omit has_active_team (fail open, not hidden by default)', () => {
      const result = visibleWorkspacePickerEntries([staffed, unknown], null);
      expect(result.map((w) => w.workspace_id)).toEqual([
        'workspace_dashpro',
        'workspace_legacy',
      ]);
    });

    it('never hides the currently selected workspace, even if inactive', () => {
      const result = visibleWorkspacePickerEntries(
        [staffed, unstaffed],
        'workspace_bkkinnovationhub',
      );
      expect(result.map((w) => w.workspace_id)).toEqual([
        'workspace_dashpro',
        'workspace_bkkinnovationhub',
      ]);
    });

    it('returns an empty list when every entry is inactive and none is selected', () => {
      expect(visibleWorkspacePickerEntries([unstaffed], null)).toEqual([]);
    });

    it('uses auto_enabled as the operator on/off source of truth when present', () => {
      const autoOnWithoutStaff: WorkspaceRecord = {
        workspace_id: 'MoveIT',
        has_active_team: false,
        auto_enabled: true,
      };
      const autoOffWithStaff: WorkspaceRecord = {
        workspace_id: 'workspace_dashpro',
        has_active_team: true,
        auto_enabled: false,
      };

      expect(
        visibleWorkspacePickerEntries([autoOnWithoutStaff, autoOffWithStaff], null).map(
          (workspace) => workspace.workspace_id,
        ),
      ).toEqual(['MoveIT']);
    });

    it('can overlay live AUTO prefs onto stale workspace records before filtering', () => {
      const staleRecords: WorkspaceRecord[] = [
        { workspace_id: 'MoveIT', has_active_team: false },
        { workspace_id: 'workspace_dashpro', has_active_team: true },
      ];

      const withLiveState = applyWorkspacePickerAutoState(staleRecords, {
        MoveIT: true,
        workspace_dashpro: false,
      });

      expect(visibleWorkspacePickerEntries(withLiveState, null).map((w) => w.workspace_id)).toEqual([
        'MoveIT',
      ]);
    });
  });
});
