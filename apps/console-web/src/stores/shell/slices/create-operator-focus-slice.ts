import type { Ref } from 'vue';

import type { OperatorBriefing } from '../../../contracts/canonical';
import type { OperatorCenterView } from '../../../lib/operator-brain-graph-view';
import { persistOperatorCenterView } from '../../../lib/operator-brain-graph-view';
import {
  resolveAttentionFocusScrollTarget,
  resolveDefaultHighlightedSignalId,
} from '../../../lib/ide-attention-focus';
import { persistIdeExplorerCollapsed } from '../../../lib/ide-layout-prefs';
import type { DockHeroMode } from '../../../lib/dock-hero-mode';
import type { LeftSidebarMode } from '../../../lib/left-sidebar-mode';
import type { LayoutMode } from '../types';

interface CreateOperatorFocusSliceInput {
  layoutMode: Ref<LayoutMode>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  highlightedSignalId: Ref<string | null>;
  ideAttentionPanelOpen: Ref<boolean>;
  ideBriefingPanelOpen: Ref<boolean>;
  ideExplorerCollapsed: Ref<boolean>;
  signalsSeamEmphasized: Ref<boolean>;
  missionControlEmphasized: Ref<boolean>;
  briefingSeamEmphasized: Ref<boolean>;
  operatorCenterView: Ref<OperatorCenterView>;
  dockHeroMode: Ref<DockHeroMode>;
  setLeftSidebarMode: (mode: LeftSidebarMode) => void;
  setDockHeroMode: (mode: DockHeroMode) => void;
  restoreComposerDraft: (content: string) => void;
}

export function createOperatorFocusSlice(input: CreateOperatorFocusSliceInput) {
  function closeIdeAttentionPanel(): void {
    input.ideAttentionPanelOpen.value = false;
    input.highlightedSignalId.value = null;
  }

  function closeIdeBriefingPanel(): void {
    input.ideBriefingPanelOpen.value = false;
  }

  function openIdeBriefingPanel(): void {
    input.ideBriefingPanelOpen.value = true;
    input.ideAttentionPanelOpen.value = false;
    input.ideExplorerCollapsed.value = false;
    persistIdeExplorerCollapsed(false);
  }

  function focusAttentionSidebar(signalId?: string | null): void {
    const topSignals = input.operatorBriefing.value?.top_signals ?? [];
    input.highlightedSignalId.value = resolveDefaultHighlightedSignalId(topSignals, signalId);

    if (input.layoutMode.value === 'ide') {
      input.ideAttentionPanelOpen.value = true;
      input.ideBriefingPanelOpen.value = false;
      input.ideExplorerCollapsed.value = false;
      persistIdeExplorerCollapsed(false);
    } else {
      input.setLeftSidebarMode('attention');
    }

    input.signalsSeamEmphasized.value = true;
    if (typeof window !== 'undefined') {
      const scrollTargetId = resolveAttentionFocusScrollTarget(input.layoutMode.value);
      window.requestAnimationFrame(() => {
        document.getElementById(scrollTargetId)?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          input.signalsSeamEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function toggleSignalDetails(signalId: string): void {
    input.highlightedSignalId.value =
      input.highlightedSignalId.value === signalId ? null : signalId;
  }

  function focusMissionControl(): void {
    input.missionControlEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('operator-mission-control')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          input.missionControlEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function setOperatorCenterView(view: OperatorCenterView): void {
    input.operatorCenterView.value = view;
    persistOperatorCenterView(view);
  }

  function afterRunLifecycleMutation(): void {
    focusMissionControl();
    if (input.dockHeroMode.value === 'briefing' && typeof window !== 'undefined') {
      input.briefingSeamEmphasized.value = true;
      window.setTimeout(() => {
        input.briefingSeamEmphasized.value = false;
      }, 1200);
    }
  }

  function focusKairoBriefing(): void {
    if (input.layoutMode.value === 'ide') {
      openIdeBriefingPanel();
    } else {
      input.setDockHeroMode('briefing');
    }
    input.briefingSeamEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        const targetId =
          input.layoutMode.value === 'ide' ? 'ide-briefing-panel' : 'dock-seam-briefing';
        document.getElementById(targetId)?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.setTimeout(() => {
          input.briefingSeamEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function focusCommandSeam(example: string): void {
    input.restoreComposerDraft(example);
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('operator-command-input')?.focus();
        document.getElementById('dock-seam-briefing')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      });
    }
  }

  return {
    focusAttentionSidebar,
    closeIdeAttentionPanel,
    closeIdeBriefingPanel,
    openIdeBriefingPanel,
    toggleSignalDetails,
    focusMissionControl,
    setOperatorCenterView,
    afterRunLifecycleMutation,
    focusKairoBriefing,
    focusCommandSeam,
  };
}
