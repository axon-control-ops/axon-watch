import { describe, expect, it } from 'vitest';

import {
  buildFleetHealthGridCells,
  fleetHealthHeadline,
  sortFleetHealthRows,
  type FleetHealthSnapshot,
} from './operator-fleet-health-view';

const snapshot: FleetHealthSnapshot = {
  generated_at: '2026-07-07T20:00:00Z',
  watch_connected: true,
  connectors: {
    configured: 4,
    ok: 3,
    degraded: 1,
    unavailable: 0,
    required_unavailable: 0,
  },
  degraded: { active: false, reasons: [] },
  count: 3,
  items: [
    {
      workspace_id: 'workspace_smoke',
      display_name: 'Smoke',
      connection_kind: 'isolated_root',
      health: 'nominal',
      active_runs: 0,
      review_ready_count: 0,
      executing_count: 0,
      pending_approvals_count: 0,
      open_signals_count: 0,
      critical_signals_count: 0,
      top_signal_title: null,
    },
    {
      workspace_id: 'workspace_dashpro',
      display_name: 'DashPro',
      connection_kind: 'project_path',
      health: 'attention',
      active_runs: 2,
      review_ready_count: 1,
      executing_count: 1,
      pending_approvals_count: 0,
      open_signals_count: 1,
      critical_signals_count: 0,
      top_signal_title: 'Sentry spike',
    },
    {
      workspace_id: 'workspace_axon_watch',
      display_name: 'Axon Watch',
      connection_kind: 'project_path',
      health: 'nominal',
      active_runs: 0,
      review_ready_count: 0,
      executing_count: 0,
      pending_approvals_count: 0,
      open_signals_count: 0,
      critical_signals_count: 0,
      top_signal_title: null,
    },
  ],
};

describe('operator-fleet-health-view', () => {
  it('prioritizes bound project workspaces and attention rows', () => {
    const sorted = sortFleetHealthRows(snapshot.items, [
      { workspace_id: 'workspace_dashpro', connection_kind: 'project_path' },
      { workspace_id: 'workspace_axon_watch', connection_kind: 'project_path' },
      { workspace_id: 'workspace_smoke', connection_kind: 'isolated_root' },
    ]);

    expect(sorted[0]?.workspace_id).toBe('workspace_axon_watch');
    expect(sorted[1]?.workspace_id).toBe('workspace_dashpro');
  });

  it('builds grid cells with selected workspace marker', () => {
    const cells = buildFleetHealthGridCells({
      snapshot,
      workspaces: [
        { workspace_id: 'workspace_dashpro', connection_kind: 'project_path' },
        { workspace_id: 'workspace_axon_watch', connection_kind: 'project_path' },
      ],
      selectedWorkspaceId: 'workspace_dashpro',
    });

    expect(cells.find((cell) => cell.workspaceId === 'workspace_dashpro')?.isSelected).toBe(true);
    expect(cells.find((cell) => cell.workspaceId === 'workspace_dashpro')?.summary).toContain(
      'review',
    );
  });

  it('always keeps the selected workspace on the grid even past the cap', () => {
    const many: FleetHealthSnapshot = {
      ...snapshot,
      count: 14,
      items: Array.from({ length: 14 }, (_, index) => ({
        workspace_id: `workspace_bound_${index}`,
        display_name: `Bound ${index}`,
        connection_kind: 'project_path',
        health: 'nominal' as const,
        active_runs: 0,
        review_ready_count: 0,
        executing_count: 0,
        pending_approvals_count: 0,
        open_signals_count: 0,
        critical_signals_count: 0,
        top_signal_title: null,
      })),
    };
    many.items.push({
      workspace_id: 'workspace_tps',
      display_name: 'TPS',
      connection_kind: 'project_path',
      health: 'nominal',
      active_runs: 0,
      review_ready_count: 0,
      executing_count: 0,
      pending_approvals_count: 0,
      open_signals_count: 0,
      critical_signals_count: 0,
      top_signal_title: null,
    });
    const workspaces = many.items.map((item) => ({
      workspace_id: item.workspace_id,
      connection_kind: 'project_path' as const,
    }));
    const cells = buildFleetHealthGridCells({
      snapshot: many,
      workspaces,
      selectedWorkspaceId: 'workspace_tps',
      maxRows: 4,
    });
    expect(cells.some((cell) => cell.workspaceId === 'workspace_tps')).toBe(true);
    expect(cells.find((cell) => cell.workspaceId === 'workspace_tps')?.isSelected).toBe(true);
  });
});
