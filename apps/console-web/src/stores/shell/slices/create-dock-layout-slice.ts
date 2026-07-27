import type { ComputedRef, Ref } from 'vue';

import type {
  InboxItem,
  RuntimeSummary,
  OperatorBriefing,
  RunRecord,
} from '../../../contracts/canonical';
import type { DockSeamId, DockSeamLayoutState } from '../../../lib/dock-seam-layout';
import {
  persistDockHeroMode,
} from '../../../lib/dock-hero-prefs';
import {
  resolveDefaultDockHeroMode,
  type DockHeroMode,
} from '../../../lib/dock-hero-mode';
import {
  persistLeftSidebarMode,
  resolveDefaultLeftSidebarMode,
  type LeftSidebarMode,
} from '../../../lib/left-sidebar-mode';
import { briefingHasOpenLoops } from '../../../lib/briefing-open-loops-view';
import { countActionableOpenSignals } from '../../../lib/operator-signal-count';
import type { LayoutMode } from '../types';

interface CreateDockLayoutSliceInput {
  layoutMode: Ref<LayoutMode>;
  dockSeamLayout: ComputedRef<DockSeamLayoutState[]>;
  expandedDockSeams: Ref<Set<DockSeamId>>;
  dockThreadSeamTouched: Ref<boolean>;
  pendingApprovalsCount: ComputedRef<number>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  runtimeSummary: Ref<RuntimeSummary | null>;
  inboxItems: Ref<InboxItem[]>;
  primaryActiveRun: ComputedRef<RunRecord | null>;
  currentWorkspaceId: ComputedRef<string | null>;
  operatorThreadMessageCount: ComputedRef<number>;
  leftSidebarMode: Ref<LeftSidebarMode>;
  leftSidebarModeTouched: Ref<boolean>;
  dockHeroMode: Ref<DockHeroMode>;
  dockHeroModeTouched: Ref<boolean>;
  briefingSeamEmphasized: Ref<boolean>;
}

export function createDockLayoutSlice(input: CreateDockLayoutSliceInput) {
  function dockSeamState(id: DockSeamId) {
    return input.dockSeamLayout.value.find((seam) => seam.id === id) ?? null;
  }

  function toggleDockSeam(id: DockSeamId): void {
    if (id === 'thread') {
      input.dockThreadSeamTouched.value = true;
    }
    const next = new Set(input.expandedDockSeams.value);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    input.expandedDockSeams.value = next;
  }

  function applyOperatorDockDefaults(): void {
    if (input.layoutMode.value !== 'operator') {
      return;
    }
    const next = new Set(input.expandedDockSeams.value);
    const workspaceId = input.currentWorkspaceId.value;
    const fleetActiveRuns =
      input.runtimeSummary.value?.active_runs ??
      input.operatorBriefing.value?.active_runs ??
      [];
    const workspaceActiveRunCount = workspaceId
      ? fleetActiveRuns.filter((run) => run.workspace_id === workspaceId).length
      : fleetActiveRuns.length;
    const openLoopOptions = {
      primaryActiveRun: input.primaryActiveRun.value,
      fleetActiveRuns,
      workspaceId,
    };
    const openLoops = briefingHasOpenLoops(input.operatorBriefing.value, openLoopOptions);
    if (!input.dockThreadSeamTouched.value) {
      // LIVE OPERATIONS orb card lives in the thread seam — keep it expanded on Mission Control.
      next.add('thread');
    }
    input.expandedDockSeams.value = next;
    if (!input.leftSidebarModeTouched.value) {
      input.leftSidebarMode.value = resolveDefaultLeftSidebarMode({
        pendingApprovals: input.pendingApprovalsCount.value,
        briefing: input.operatorBriefing.value,
      });
    }
    if (!input.dockHeroModeTouched.value) {
      const activeRunCount = Math.max(
        input.primaryActiveRun.value ? 1 : 0,
        workspaceActiveRunCount,
      );
      input.dockHeroMode.value = resolveDefaultDockHeroMode({
        pendingApprovals: input.pendingApprovalsCount.value,
        criticalSignals: input.runtimeSummary.value?.signals.critical_count ?? 0,
        highSignals: input.runtimeSummary.value?.signals.high_count ?? 0,
        nextSafeActions: input.operatorBriefing.value?.next_safe_actions.length ?? 0,
        actionableInboxCount: countActionableOpenSignals(input.inboxItems.value),
        activeRunCount,
        hasOpenLoops: openLoops,
      });
    }
  }

  function setLeftSidebarMode(mode: LeftSidebarMode): void {
    input.leftSidebarModeTouched.value = true;
    input.leftSidebarMode.value = mode;
    persistLeftSidebarMode(mode);
  }

  function setDockHeroMode(mode: DockHeroMode): void {
    input.dockHeroModeTouched.value = true;
    input.dockHeroMode.value = mode;
    persistDockHeroMode(mode);
    // Clear stale emphasis when leaving briefing; focusKairoBriefing re-arms it on open.
    if (mode !== 'briefing') {
      input.briefingSeamEmphasized.value = false;
    }
  }

  function toggleDockHeroMode(): void {
    setDockHeroMode(input.dockHeroMode.value === 'command' ? 'briefing' : 'command');
  }

  return {
    applyOperatorDockDefaults,
    dockSeamState,
    setDockHeroMode,
    setLeftSidebarMode,
    toggleDockHeroMode,
    toggleDockSeam,
  };
}
