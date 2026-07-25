import type { FleetHealthSnapshot, FleetHealthWorkspaceRow } from '../../lib/operator-fleet-health-view';
import type { BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import type { WorkspaceRecord } from '../../contracts/canonical';
import {
  galaxyMockupRailItems,
  type GalaxyMockupRailItem,
} from './galaxy-mockup-rail-view';

export type GalaxyRailChip = {
  id: string;
  label: string;
  tone: 'nominal' | 'attention' | 'critical' | 'info';
};

export type GalaxyRailItemWithChips = GalaxyMockupRailItem & {
  chips: GalaxyRailChip[];
};

function fleetRowFor(
  fleet: FleetHealthSnapshot | null,
  workspaceId: string | null,
): FleetHealthWorkspaceRow | null {
  if (!fleet || !workspaceId) {
    return null;
  }
  return fleet.items.find((row) => row.workspace_id === workspaceId) ?? null;
}

export function galaxyWorkspaceRailChips(
  row: FleetHealthWorkspaceRow | null,
): GalaxyRailChip[] {
  if (!row) {
    return [];
  }
  const chips: GalaxyRailChip[] = [];
  if (row.executing_count > 0) {
    chips.push({
      id: 'run',
      label: `${row.executing_count} run`,
      tone: 'info',
    });
  }
  if (row.pending_approvals_count > 0) {
    chips.push({
      id: 'approval',
      label: `${row.pending_approvals_count} appr`,
      tone: 'critical',
    });
  }
  if (row.critical_signals_count > 0) {
    chips.push({
      id: 'critical',
      label: `${row.critical_signals_count} crit`,
      tone: 'critical',
    });
  } else if (row.open_signals_count > 0) {
    chips.push({
      id: 'signal',
      label: `${row.open_signals_count} sig`,
      tone: 'attention',
    });
  }
  if (row.health !== 'nominal') {
    chips.push({
      id: 'health',
      label: row.health,
      tone: row.health,
    });
  }
  return chips.slice(0, 4);
}

export function galaxyMockupRailItemsWithChips(
  snapshot: BrainGraphSnapshot | null,
  workspaces: WorkspaceRecord[],
  fleet: FleetHealthSnapshot | null,
): GalaxyRailItemWithChips[] {
  return galaxyMockupRailItems(snapshot, workspaces).map((item) => ({
    ...item,
    chips: galaxyWorkspaceRailChips(fleetRowFor(fleet, item.workspace_id)),
  }));
}
