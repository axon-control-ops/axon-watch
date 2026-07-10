import type { ComputedRef, Ref } from 'vue';

import type { RuntimeSummary, OperatorBriefing } from '../../../contracts/canonical';
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
import type { LayoutMode } from '../types';

interface CreateDockLayoutSliceInput {
  layoutMode: Ref<LayoutMode>;
  dockSeamLayout: ComputedRef<DockSeamLayoutState[]>;
  expandedDockSeams: Ref<Set<DockSeamId>>;
  pendingApprovalsCount: ComputedRef<number>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  runtimeSummary: Ref<RuntimeSummary | null>;
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
    next.add('thread');
    input.expandedDockSeams.value = next;
    if (!input.leftSidebarModeTouched.value) {
      input.leftSidebarMode.value = resolveDefaultLeftSidebarMode({
        pendingApprovals: input.pendingApprovalsCount.value,
        briefing: input.operatorBriefing.value,
      });
    }
    if (!input.dockHeroModeTouched.value) {
      input.dockHeroMode.value = resolveDefaultDockHeroMode({
        pendingApprovals: input.pendingApprovalsCount.value,
        criticalSignals: input.runtimeSummary.value?.signals.critical_count ?? 0,
        highSignals: input.runtimeSummary.value?.signals.high_count ?? 0,
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
    if (mode === 'briefing') {
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
