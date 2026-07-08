import { describe, expect, it } from 'vitest';

import type { WorkspaceRecord } from '../contracts/canonical';

import {
  defaultOperatorWorkspaceId,
  mergeOperatorWorkspaceCatalog,
  workspaceCatalogMode,
  workspaceDisplayLabel,
} from './operator-workspace-catalog';

const mockupItems: WorkspaceRecord[] = [
  { workspace_id: 'workspace_smoke', connection_kind: 'isolated_root' },
  { workspace_id: 'workspace_nlp', connection_kind: 'isolated_root' },
];

const productionItems: WorkspaceRecord[] = [
  {
    workspace_id: 'workspace_axon_watch',
    connection_kind: 'project_path',
    project_root: '/home/edp/axon-nvme/repos/axon-watch',
    display_name: 'axon-watch',
  },
  {
    workspace_id: 'workspace_axon_local',
    connection_kind: 'project_path',
    project_root: '/home/edp/axon-nvme/repos/axon-local',
    display_name: 'axon-local',
  },
  { workspace_id: 'workspace_smoke', connection_kind: 'isolated_root' },
];

describe('operator workspace catalog', () => {
  it('uses mockup catalog when no bound project workspaces exist', () => {
    expect(workspaceCatalogMode(mockupItems)).toBe('mockup');
    expect(mergeOperatorWorkspaceCatalog(mockupItems).map((item) => item.workspace_id)).toEqual([
      'workspace_smoke',
      'workspace_recsys',
      'workspace_finance',
      'workspace_nlp',
      'workspace_cv',
      'workspace_edge',
      'workspace_research',
    ]);
  });

  it('prefers axon-watch and axon-local when project bindings exist', () => {
    expect(workspaceCatalogMode(productionItems)).toBe('production');
    expect(mergeOperatorWorkspaceCatalog(productionItems).map((item) => item.workspace_id)).toEqual([
      'workspace_axon_watch',
      'workspace_axon_local',
    ]);
  });

  it('includes additional bound child workspaces after axon-watch and axon-local', () => {
    const withChild: WorkspaceRecord[] = [
      ...productionItems,
      {
        workspace_id: 'workspace_dashpro',
        connection_kind: 'project_path',
        project_root: '/home/edp/Projectx/product/dashpro',
        display_name: 'DashPro',
      },
    ];
    expect(mergeOperatorWorkspaceCatalog(withChild).map((item) => item.workspace_id)).toEqual([
      'workspace_axon_watch',
      'workspace_axon_local',
      'workspace_dashpro',
    ]);
  });

  it('defaults to workspace_axon_watch in production catalog mode', () => {
    expect(defaultOperatorWorkspaceId(mergeOperatorWorkspaceCatalog(productionItems))).toBe(
      'workspace_axon_watch',
    );
  });

  it('shows canonical labels for bound workspaces', () => {
    expect(workspaceDisplayLabel(productionItems[0]!)).toBe('Axon Watch');
    expect(workspaceDisplayLabel(productionItems[1]!)).toBe('Axon Local');
  });
});
