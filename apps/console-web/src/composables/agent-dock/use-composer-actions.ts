import type { Ref } from 'vue';

import {
  shouldSteerAgentDockComposer,
  shouldSubmitAgentDockComposer,
} from '../../lib/agent-dock-composer-input';
import {
  shouldRecallNextAgentComposerHistory,
  shouldRecallPreviousAgentComposerHistory,
} from '../../lib/agent-dock-composer-history';
import {
  clearBriefingSurfaceOffer,
  shouldOpenBriefingFromFollowup,
} from '../../features/kairo-conversation/conversation-briefing-surface';
import { kairoConversationReply } from '../../features/kairo-conversation/kairo-conversation-state';
import type { ComposerClipboardImage } from '../../lib/composer-clipboard-paste';
import {
  applyEmployeeSpecialtyRoute,
  dismissEmployeeSpecialtyRoute,
  undoEmployeeSpecialtyRoute,
} from '../../lib/apply-employee-specialty-route';
import { shouldSoftSwitchAgentToPlan } from '../../lib/composer-plan-auto-switch';
import { resolveEmployeeSpecialtyRoute } from '../../lib/resolve-employee-specialty-route';
import { DEBUG_REPRODUCE_PROCEED_MESSAGE } from '../../lib/debug-reproduce-view';
import {
  findIdeComposerQueueEntry,
  type IdeComposerMode,
} from '../../lib/ide-composer-queue';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import {
  type TeammateRouteNotice,
} from '../../lib/teammate-route-notice';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';

type ShellStore = ReturnType<typeof useShellStore>;

export type PlanSoftSwitchNotice = {
  reason: string;
  previousMode: 'agent';
  /** Cursor-like: 'switched' already flipped mode; 'offer' pauses until user chooses. */
  kind?: 'switched' | 'offer';
  /** Draft held while an offer is pending (not yet submitted). */
  pendingDraft?: string;
};

export type { TeammateRouteNotice };

type UseComposerActionsOptions = {
  shell: ShellStore;
  composerMode: Ref<ComposerMode>;
  inputRef: Ref<HTMLTextAreaElement | null>;
  kairoDraft: Ref<string>;
  composerImages: Ref<ComposerClipboardImage[]>;
  composerHistory: Ref<string[]>;
  composerHistoryIndex: Ref<number>;
  submitKairoTurn: (draft: string) => Promise<void>;
  recordComposerHistoryIfSent: (draft: string) => void;
  handleHistory: (direction: 'previous' | 'next') => void;
  speechCapture: { capturing: Ref<boolean> };
  startVoiceCapture: () => void;
  stopVoiceCapture: () => void;
  onDebugReproduceProceed?: (messageId: string) => void;
  planSoftSwitchNotice: Ref<PlanSoftSwitchNotice | null>;
  teammateRouteNotice: Ref<TeammateRouteNotice | null>;
  /** Return true when `/` or `@` typeahead consumed the key. */
  handleTypeaheadKeydown?: (event: KeyboardEvent) => boolean;
  /** Merge Cursor-style skill chips into the draft right before submit/steer. */
  withSkillTokensForSubmit?: (draft: string) => string;
  clearSkillAttachments?: () => void;
};

export function useComposerActions(options: UseComposerActionsOptions) {
  const {
    shell,
    composerMode,
    inputRef,
    kairoDraft,
    composerImages,
    composerHistory,
    composerHistoryIndex,
    submitKairoTurn,
    recordComposerHistoryIfSent,
    handleHistory,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
    onDebugReproduceProceed,
    planSoftSwitchNotice,
    teammateRouteNotice,
    handleTypeaheadKeydown,
    withSkillTokensForSubmit,
    clearSkillAttachments,
  } = options;

  function handleApproveRun(): void {
    void shell.approveIdeAgentRun();
  }

  function handleRejectRun(): void {
    void shell.rejectIdeAgentRun();
  }

  function handleStopRun(): void {
    void shell.stopIdeAgentRun();
  }

  function handleResumeRun(): void {
    void shell.resumeIdeAgentRun();
  }

  function toggleVoiceCapture(): void {
    if (speechCapture.capturing.value) {
      stopVoiceCapture();
      return;
    }
    shell.interruptKairoVoice();
    startVoiceCapture();
  }

  async function handleDebugReproduceProceed(messageId: string): Promise<void> {
    if (composerMode.value !== 'debug' && shell.ideAgentLinkedRun?.mode !== 'debug') {
      composerMode.value = 'debug';
    }
    onDebugReproduceProceed?.(messageId);
    shell.ideComposerDraft = DEBUG_REPRODUCE_PROCEED_MESSAGE;
    await shell.submitIdeComposer('debug');
  }

  async function handleSubmit(event?: Event): Promise<void> {
    event?.preventDefault();
    const draft =
      composerMode.value === 'kairo' ? kairoDraft.value.trim() : shell.ideComposerDraft.trim();
    if (shouldOpenBriefingFromFollowup(draft)) {
      clearBriefingSurfaceOffer();
      kairoConversationReply.value = '';
      shell.focusKairoBriefing();
      if (composerMode.value === 'kairo') {
        kairoDraft.value = '';
      } else {
        shell.ideComposerDraft = '';
      }
      clearSkillAttachments?.();
      return;
    }
    if (composerMode.value === 'kairo') {
      await submitKairoTurn(draft);
      return;
    }
    let modeForSubmit: IdeComposerMode = composerMode.value;
    const submitDraft = withSkillTokensForSubmit?.(shell.ideComposerDraft) ?? shell.ideComposerDraft;
    if (modeForSubmit === 'agent') {
      const decision = shouldSoftSwitchAgentToPlan(modeForSubmit, submitDraft);
      if (decision.action === 'offer') {
        // Cursor suggests Plan for complex asks — pause for explicit choice.
        planSoftSwitchNotice.value = {
          kind: 'offer',
          reason: decision.reason,
          previousMode: 'agent',
          pendingDraft: submitDraft,
        };
        return;
      }
      if (decision.action === 'switch') {
        planSoftSwitchNotice.value = {
          kind: 'switched',
          reason: decision.reason,
          previousMode: 'agent',
        };
        composerMode.value = 'plan';
        modeForSubmit = 'plan';
      }
    }

    dismissEmployeeSpecialtyRoute();
    const workspaceId = shell.currentWorkspace?.workspace_id ?? '';
    const submitStartedAt = Date.now();
    // Deterministic specialty route only on the send path. Model tie-break runs a
    // full ask-mode composer call (up to 45s) and was blocking Enter/send before
    // the real agent run started.
    const routeDecision = await resolveEmployeeSpecialtyRoute({
      prompt: submitDraft,
      workspaceId,
      currentEmployee: shell.activeIdeEmployeeRecord,
      roster: shell.companyEmployeesForCurrentWorkspace,
      useModelTiebreak: false,
    });
    const routeMs = Date.now() - submitStartedAt;
    if (routeDecision.shouldRoute) {
      await applyEmployeeSpecialtyRoute(shell, routeDecision);
    }
    const applyMs = Date.now() - submitStartedAt;

    const attachmentFiles = composerImages.value.map((image) => image.file);
    // openOrFocusEmployeeIdeThread may clear/restore drafts — keep the routed prompt.
    shell.ideComposerDraft = submitDraft;
    await shell.submitIdeComposer(modeForSubmit, { attachmentFiles });
    clearSkillAttachments?.();
    recordComposerHistoryIfSent(draft);
  }

  function undoPlanSoftSwitch(): void {
    const notice = planSoftSwitchNotice.value;
    if (!notice) {
      return;
    }
    if (notice.kind === 'offer') {
      planSoftSwitchNotice.value = null;
      return;
    }
    composerMode.value = notice.previousMode;
    planSoftSwitchNotice.value = null;
  }

  function dismissPlanSoftSwitch(): void {
    planSoftSwitchNotice.value = null;
  }

  async function acceptPlanSoftSwitchOffer(): Promise<void> {
    const notice = planSoftSwitchNotice.value;
    if (!notice || notice.kind !== 'offer') {
      return;
    }
    const pending = (notice.pendingDraft ?? shell.ideComposerDraft).trim();
    planSoftSwitchNotice.value = null;
    if (!pending) {
      return;
    }
    composerMode.value = 'plan';
    shell.ideComposerDraft = pending;
    const attachmentFiles = composerImages.value.map((image) => image.file);
    await shell.submitIdeComposer('plan', { attachmentFiles });
    clearSkillAttachments?.();
    recordComposerHistoryIfSent(pending);
  }

  async function declinePlanSoftSwitchOffer(): Promise<void> {
    const notice = planSoftSwitchNotice.value;
    if (!notice || notice.kind !== 'offer') {
      return;
    }
    const pending = (notice.pendingDraft ?? shell.ideComposerDraft).trim();
    planSoftSwitchNotice.value = null;
    if (!pending) {
      return;
    }
    composerMode.value = 'agent';
    shell.ideComposerDraft = pending;
    dismissEmployeeSpecialtyRoute();
    const workspaceId = shell.currentWorkspace?.workspace_id ?? '';
    const routeDecision = await resolveEmployeeSpecialtyRoute({
      prompt: pending,
      workspaceId,
      currentEmployee: shell.activeIdeEmployeeRecord,
      roster: shell.companyEmployeesForCurrentWorkspace,
      useModelTiebreak: false,
    });
    if (routeDecision.shouldRoute) {
      await applyEmployeeSpecialtyRoute(shell, routeDecision);
    }
    const attachmentFiles = composerImages.value.map((image) => image.file);
    shell.ideComposerDraft = pending;
    await shell.submitIdeComposer('agent', { attachmentFiles });
    clearSkillAttachments?.();
    recordComposerHistoryIfSent(pending);
  }

  async function undoTeammateRoute(): Promise<void> {
    await undoEmployeeSpecialtyRoute(shell, teammateRouteNotice.value);
  }

  function dismissTeammateRoute(): void {
    dismissEmployeeSpecialtyRoute();
  }

  async function handleSteer(event?: Event): Promise<void> {
    event?.preventDefault();
    if (composerMode.value === 'kairo') {
      return;
    }
    const draft = shell.ideComposerDraft.trim();
    const submitDraft = withSkillTokensForSubmit?.(shell.ideComposerDraft) ?? shell.ideComposerDraft;
    shell.ideComposerDraft = submitDraft;
    const attachmentFiles = composerImages.value.map((image) => image.file);
    await shell.steerIdeComposer(composerMode.value, { attachmentFiles });
    clearSkillAttachments?.();
    recordComposerHistoryIfSent(draft);
  }

  async function handleSteerQueuedMessage(messageId: string): Promise<void> {
    if (composerMode.value === 'kairo') {
      return;
    }
    await shell.steerQueuedIdeComposerMessage(messageId);
  }

  function removeQueuedMessage(messageId: string): void {
    shell.removeIdeComposerQueuedMessage(messageId);
  }

  function editQueuedMessage(messageId: string): void {
    const entry = findIdeComposerQueueEntry(shell.ideComposerQueue, messageId);
    if (!entry) {
      return;
    }
    shell.removeIdeComposerQueuedMessage(messageId);
    composerMode.value = entry.composerMode;
    shell.ideComposerDraft = entry.content;
    focusAgentDockComposerInput();
  }

  function revealComposerTerminalPanel(): void {
    shell.revealIdeTerminalPanel();
  }

  function handleComposerKeydown(event: KeyboardEvent): void {
    if (handleTypeaheadKeydown?.(event)) {
      return;
    }

    if (inputRef.value) {
      if (
        shouldRecallPreviousAgentComposerHistory({
          key: event.key,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          ctrlKey: event.ctrlKey,
          metaKey: event.metaKey,
          selectionStart: inputRef.value.selectionStart,
          selectionEnd: inputRef.value.selectionEnd,
          value: inputRef.value.value,
        }) &&
        composerHistory.value.length > 0
      ) {
        event.preventDefault();
        handleHistory('previous');
        return;
      }

      if (
        shouldRecallNextAgentComposerHistory(
          {
            key: event.key,
            shiftKey: event.shiftKey,
            altKey: event.altKey,
            ctrlKey: event.ctrlKey,
            metaKey: event.metaKey,
            selectionStart: inputRef.value.selectionStart,
            selectionEnd: inputRef.value.selectionEnd,
            value: inputRef.value.value,
          },
          composerHistoryIndex.value >= 0,
        )
      ) {
        event.preventDefault();
        handleHistory('next');
        return;
      }
    }

    if (shouldSteerAgentDockComposer(event)) {
      event.preventDefault();
      void handleSteer();
      return;
    }

    if (!shouldSubmitAgentDockComposer(event)) {
      return;
    }
    event.preventDefault();
    void handleSubmit();
  }

  return {
    acceptPlanSoftSwitchOffer,
    declinePlanSoftSwitchOffer,
    dismissPlanSoftSwitch,
    dismissTeammateRoute,
    handleApproveRun,
    handleComposerKeydown,
    handleDebugReproduceProceed,
    handleRejectRun,
    handleResumeRun,
    handleSteer,
    handleSteerQueuedMessage,
    handleStopRun,
    handleSubmit,
    editQueuedMessage,
    removeQueuedMessage,
    revealComposerTerminalPanel,
    toggleVoiceCapture,
    undoPlanSoftSwitch,
    undoTeammateRoute,
  };
}
