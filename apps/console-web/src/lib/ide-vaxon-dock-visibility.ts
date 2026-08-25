import { computed, type ComputedRef } from 'vue';

import { isKairoVoiceFollowupWindowActive } from './kairo-voice-followup-window';
import {
  getVaxonBriefingInteraction,
  vaxonBriefingPendingByWorkspace,
} from './vaxon-briefing-interaction';
import { vaxonLineAsksForReply } from './vaxon-reply-prompt';

export type IdeVaxonDockVisibilityInput = {
  layoutMode: string;
  ideActivityView: string;
  workspaceId: string | null | undefined;
  kairoSpeechActive: boolean;
  liveSpokenText: string | null | undefined;
  stickySpokenText: string | null | undefined;
  stickyNeedsDecision: boolean;
  /** Operator opened VAXON via the activity-bar V control. */
  operatorPinned?: boolean;
};

/** Team roster owns the rail — VAXON pops up only while speaking or awaiting a reply. */
export function shouldShowIdeVaxonDock(input: IdeVaxonDockVisibilityInput): boolean {
  if (input.layoutMode !== 'ide') {
    return true;
  }
  if (input.operatorPinned) {
    return true;
  }
  if (input.ideActivityView !== 'team') {
    return true;
  }
  if (input.kairoSpeechActive || input.liveSpokenText?.trim()) {
    return true;
  }
  if (input.stickyNeedsDecision) {
    return true;
  }
  const ws = input.workspaceId?.trim();
  if (ws) {
    const pending = getVaxonBriefingInteraction(ws);
    if (pending?.line.trim() && vaxonLineAsksForReply(pending.line)) {
      return true;
    }
  }
  if (
    isKairoVoiceFollowupWindowActive() &&
    input.stickySpokenText?.trim() &&
    vaxonLineAsksForReply(input.stickySpokenText)
  ) {
    return true;
  }
  return false;
}

export function useIdeVaxonDockVisibility(input: {
  shell: {
    layoutMode: string;
    ideActivityView: string;
    currentWorkspace: { workspace_id?: string } | null | undefined;
    kairoSpeechActive: boolean;
  };
  liveSpokenText: ComputedRef<string | null | undefined>;
  stickySpokenText: ComputedRef<string | null | undefined>;
  stickyNeedsDecision: ComputedRef<boolean>;
  operatorPinned: ComputedRef<boolean>;
}): {
  teamViewOpen: ComputedRef<boolean>;
  showIdeVaxonDock: ComputedRef<boolean>;
  teamPanelFullHeight: ComputedRef<boolean>;
} {
  const teamViewOpen = computed(
    () => input.shell.layoutMode === 'ide' && input.shell.ideActivityView === 'team',
  );
  const showIdeVaxonDock = computed(() => {
    void vaxonBriefingPendingByWorkspace.value;
    return shouldShowIdeVaxonDock({
      layoutMode: input.shell.layoutMode,
      ideActivityView: input.shell.ideActivityView,
      workspaceId: input.shell.currentWorkspace?.workspace_id,
      kairoSpeechActive: input.shell.kairoSpeechActive,
      liveSpokenText: input.liveSpokenText.value,
      stickySpokenText: input.stickySpokenText.value,
      stickyNeedsDecision: input.stickyNeedsDecision.value,
      operatorPinned: input.operatorPinned.value,
    });
  });
  const teamPanelFullHeight = computed(
    () => teamViewOpen.value && !showIdeVaxonDock.value,
  );
  return { teamViewOpen, showIdeVaxonDock, teamPanelFullHeight };
}
