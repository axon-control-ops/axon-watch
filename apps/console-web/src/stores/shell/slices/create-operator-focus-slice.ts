import type { Ref } from 'vue';

import type { OperatorBriefing } from '../../../contracts/canonical';
import type { OperatorCenterView } from '../../../lib/operator-brain-graph-view';
import { persistOperatorCenterView } from '../../../lib/operator-brain-graph-view';
import {
  resolveAttentionFocusScrollTarget,
  resolveDefaultHighlightedSignalId,
  type AttentionTopSignal,
} from '../../../lib/ide-attention-focus';
import { persistIdeExplorerCollapsed } from '../../../lib/ide-layout-prefs';
import type { DockSeamId } from '../../../lib/dock-seam-layout';
import type { DockHeroMode } from '../../../lib/dock-hero-mode';
import type { LayoutMode } from '../types';

interface CreateOperatorFocusSliceInput {
  layoutMode: Ref<LayoutMode>;
  operatorBriefing: Ref<OperatorBriefing | null>;
  attentionSignals?: Readonly<Ref<readonly AttentionTopSignal[]>>;
  highlightedSignalId: Ref<string | null>;
  ideAttentionPanelOpen: Ref<boolean>;
  ideBriefingPanelOpen: Ref<boolean>;
  ideExplorerCollapsed: Ref<boolean>;
  signalsSeamEmphasized: Ref<boolean>;
  missionControlEmphasized: Ref<boolean>;
  connectorsEmphasized: Ref<boolean>;
  briefingSeamEmphasized: Ref<boolean>;
  operatorCenterView: Ref<OperatorCenterView>;
  dockHeroMode: Ref<DockHeroMode>;
  expandedDockSeams: Ref<Set<DockSeamId>>;
  dockThreadSeamTouched: Ref<boolean>;
  setDockHeroMode: (mode: DockHeroMode) => void;
  restoreComposerDraft: (content: string) => void;
  setLayoutMode: (mode: LayoutMode) => void;
  setCurrentWorkspace: (workspaceId: string) => void;
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

  /** IDE activity-bar Attention control: open stack or close if already open. */
  function toggleIdeAttentionPanel(): void {
    if (input.layoutMode.value !== 'ide') {
      focusAttentionSidebar();
      return;
    }
    if (input.ideAttentionPanelOpen.value) {
      closeIdeAttentionPanel();
      return;
    }
    focusAttentionSidebar();
  }

  function focusAttentionSidebar(signalId?: string | null): void {
    const topSignals = input.operatorBriefing.value?.top_signals ?? [];
    const focusSignals: AttentionTopSignal[] = [];
    const seenSignalIds = new Set<string>();
    for (const signal of [...(input.attentionSignals?.value ?? []), ...topSignals]) {
      const id = signal.signal_id?.trim();
      if (!id || seenSignalIds.has(id)) {
        continue;
      }
      seenSignalIds.add(id);
      focusSignals.push(signal);
    }
    const spokenSignalId =
      input.operatorBriefing.value?.operator_presence?.spoken_alert.signal_id ?? null;
    input.highlightedSignalId.value = resolveDefaultHighlightedSignalId(
      focusSignals,
      signalId,
      spokenSignalId,
    );

    if (input.layoutMode.value === 'ide') {
      input.ideAttentionPanelOpen.value = true;
      input.ideBriefingPanelOpen.value = false;
      input.ideExplorerCollapsed.value = false;
      persistIdeExplorerCollapsed(false);
    } else {
      // Mission Control Attention strip lives under Fleet Health (left rail hidden).
      setOperatorCenterView('grid');
      const highlightedId = input.highlightedSignalId.value;
      const signalWorkspaceId =
        (highlightedId
          ? focusSignals.find((signal) => signal.signal_id === highlightedId)?.workspace_id
          : null) ??
        (signalId?.trim()
          ? focusSignals.find((signal) => signal.signal_id === signalId.trim())?.workspace_id
          : null) ??
        null;
      if (signalWorkspaceId?.trim()) {
        input.setCurrentWorkspace(signalWorkspaceId.trim());
      }
    }

    input.signalsSeamEmphasized.value = true;
    if (typeof window !== 'undefined') {
      const scrollTargetId = resolveAttentionFocusScrollTarget(input.layoutMode.value);
      window.requestAnimationFrame(() => {
        document.getElementById(scrollTargetId)?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
        window.requestAnimationFrame(() => {
          const highlightedId = input.highlightedSignalId.value;
          const highlightedRow = highlightedId
            ? [...document.querySelectorAll<HTMLElement>('[data-signal-id]')].find(
                (row) => row.dataset.signalId === highlightedId,
              )
            : null;
          highlightedRow?.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          });
        });
        if (window.location.hash === '#operator-task-board') {
          window.history.replaceState(null, '', window.location.pathname + window.location.search);
        }
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
    // Mission Control = fleet mosaic (Brain Graph is a separate center view).
    if (input.layoutMode.value === 'ide') {
      input.setLayoutMode('operator');
    }
    setOperatorCenterView('grid');
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

  function focusOperatorTaskBoard(): void {
    setOperatorCenterView('grid');
    input.missionControlEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        const board = document.getElementById('operator-task-board');
        board?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        if (window.location.hash !== '#operator-task-board') {
          window.history.replaceState(null, '', '#operator-task-board');
        }
        window.setTimeout(() => {
          input.missionControlEmphasized.value = false;
        }, 1200);
      });
    }
  }

  function focusWatchConnectors(): void {
    if (input.layoutMode.value === 'ide') {
      input.setLayoutMode('operator');
    }

    if (input.operatorCenterView.value === 'graph') {
      setOperatorCenterView('grid');
    }

    input.connectorsEmphasized.value = true;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('operator-mission-control')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
        window.requestAnimationFrame(() => {
          document.getElementById('watch-connectors-rail')?.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
          });
          window.setTimeout(() => {
            input.connectorsEmphasized.value = false;
          }, 1200);
        });
      });
    }
  }

  function setOperatorCenterView(view: OperatorCenterView): void {
    input.operatorCenterView.value = view;
    persistOperatorCenterView(view);
  }

  function afterRunLifecycleMutation(options: { preserveSurface?: boolean } = {}): void {
    // IDE Continue / resume / stop must stay on the IDE surface. Never yank the
    // operator into Mission Control mid-composer work.
    const stayOnIde = options.preserveSurface === true || input.layoutMode.value === 'ide';
    if (!stayOnIde) {
      focusMissionControl();
    }
    if (input.dockHeroMode.value === 'briefing' && typeof window !== 'undefined') {
      input.briefingSeamEmphasized.value = true;
      window.setTimeout(() => {
        input.briefingSeamEmphasized.value = false;
      }, 1200);
    }
  }

  /**
   * Briefing emphasis must never hide Mission Control Live Ops.
   * On operator grid the thread seam *is* the VAXON talk box; collapsing it
   * left an empty cyan frame with no expand chrome.
   */
  function collapseOperatorThreadForBriefing(): void {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': 'db8bb4',
      },
      body: JSON.stringify({
        sessionId: 'db8bb4',
        runId: 'vaxon-composer',
        hypothesisId: 'C2',
        location: 'create-operator-focus-slice.ts:collapseOperatorThreadForBriefing',
        message: 'Briefing focus skipped Live Ops collapse',
        data: {
          layoutMode: input.layoutMode.value,
          threadExpanded: input.expandedDockSeams.value.has('thread'),
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion
  }

  /**
   * Mission Control hosts VAXON in the LIVE OPERATIONS thread seam, not the
   * briefing seam, so briefing focus would collapse the panel we want to show.
   */
  function focusLiveOperations(): void {
    if (input.layoutMode.value === 'ide') {
      input.setLayoutMode('operator');
    }
    if (input.operatorCenterView.value === 'graph') {
      setOperatorCenterView('grid');
    }
    if (!input.expandedDockSeams.value.has('thread')) {
      const next = new Set(input.expandedDockSeams.value);
      next.add('thread');
      input.expandedDockSeams.value = next;
    }
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.getElementById('mission-control-live-ops')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        });
      });
    }
  }

  function focusKairoBriefing(): void {
    if (input.layoutMode.value === 'ide') {
      openIdeBriefingPanel();
    } else {
      input.setDockHeroMode('briefing');
      collapseOperatorThreadForBriefing();
    }
    // Retrigger emphasis even when already on briefing (class toggle).
    input.briefingSeamEmphasized.value = false;
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        input.briefingSeamEmphasized.value = true;
        const targetId =
          input.layoutMode.value === 'ide' ? 'ide-briefing-panel' : 'dock-seam-briefing';
        const target = document.getElementById(targetId);
        target?.classList.add('dock-hero-panel--focus-reveal');
        target?.scrollIntoView({
          behavior: 'smooth',
          block: 'end',
          inline: 'nearest',
        });
        document.querySelector('.region-right-dock')?.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'nearest',
        });
        window.setTimeout(() => {
          input.briefingSeamEmphasized.value = false;
          target?.classList.remove('dock-hero-panel--focus-reveal');
        }, 2200);
      });
    } else {
      input.briefingSeamEmphasized.value = true;
    }
  }

  function focusCommandSeam(example = ''): void {
    if (example.trim()) {
      input.restoreComposerDraft(example);
    }
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
    toggleIdeAttentionPanel,
    focusLiveOperations,
    closeIdeAttentionPanel,
    closeIdeBriefingPanel,
    openIdeBriefingPanel,
    toggleSignalDetails,
    focusMissionControl,
    focusOperatorTaskBoard,
    focusWatchConnectors,
    setOperatorCenterView,
    afterRunLifecycleMutation,
    focusKairoBriefing,
    focusCommandSeam,
  };
}
