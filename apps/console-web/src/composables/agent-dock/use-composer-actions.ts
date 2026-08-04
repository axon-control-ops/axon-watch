import type { Ref } from 'vue';

import {
  shouldProceedDebugReproduceComposer,
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
import {
  matchNamedAssignEmployee,
  rewriteNamedAssignPrompt,
} from '../../lib/named-assign-route';
import { resolveEmployeeSpecialtyRoute } from '../../lib/resolve-employee-specialty-route';
import { shouldApplySpecialtyRouteNow } from '../../lib/specialty-route-busy-gate';
import {
  findIdeComposerQueueEntry,
  type IdeComposerMode,
} from '../../lib/ide-composer-queue';
import { persistIdeComposerDraft } from '../../lib/ide-composer-draft-prefs';
import { focusAgentDockComposerInput } from '../../lib/agent-dock-composer-focus';
import type { TeammateRouteNotice } from '../../lib/teammate-route-notice';
import { resolveLiveBusyEmployeeIds } from '../../features/workspace-agents/company-roster-busy';
import { useShellStore } from '../../stores/shell';
import { useDebugReproduceActions } from './use-debug-reproduce-actions';
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
  dismissedDebugReproduceMessageId: Ref<string | null>;
  submitKairoTurn: (
    draft: string,
    options?: { dockAttachments?: ComposerClipboardImage[] },
  ) => Promise<boolean | void>;
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
    dismissedDebugReproduceMessageId,
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

  function liveBusyEmployeeIds(): string[] {
    return resolveLiveBusyEmployeeIds({
      employees: shell.companyEmployeesForCurrentWorkspace,
      streamingThreadIds: shell.streamingIdeThreadIds,
      threads: shell.ideThreadsForCurrentWorkspace,
      focusedStreamEmployeeId: shell.agentStreamActive
        ? shell.activeIdeThread?.employee_id?.trim() ||
          shell.activeIdeEmployeeRecord?.employee_id?.trim() ||
          null
        : null,
    });
  }

  async function maybeApplySpecialtyRoute(
    routeDecision: Awaited<ReturnType<typeof resolveEmployeeSpecialtyRoute>>,
  ): Promise<boolean> {
    if (
      !shouldApplySpecialtyRouteNow({
        decision: routeDecision,
        busyEmployeeIds: liveBusyEmployeeIds(),
      })
    ) {
      return false;
    }
    const applied = await applyEmployeeSpecialtyRoute(shell, routeDecision);
    return applied.routed;
  }

  const handleApproveRun = (): void => {
    void shell.approveIdeAgentRun();
  };
  const handleRejectRun = (): void => {
    void shell.rejectIdeAgentRun();
  };
  const handleStopRun = (): void => {
    void shell.stopIdeAgentRun();
  };
  const handleResumeRun = (): void => {
    void shell.resumeIdeAgentRun();
  };
  const toggleVoiceCapture = (): void => {
    if (speechCapture.capturing.value) {
      stopVoiceCapture();
      return;
    }
    shell.interruptKairoVoice();
    startVoiceCapture();
  };
  const {
    debugReproduceActive,
    activeDebugReproduceMessageId,
    handleDebugReproduceProceed,
  } = useDebugReproduceActions({
    shell,
    composerMode,
    composerImages,
    dismissedDebugReproduceMessageId,
    recordComposerHistoryIfSent,
    onDebugReproduceProceed,
    withSkillTokensForSubmit,
    clearSkillAttachments,
  });

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
      const dockAttachments = composerImages.value.length
        ? [...composerImages.value]
        : undefined;
      const sent = await submitKairoTurn(draft, { dockAttachments });
      if (sent !== false) {
        recordComposerHistoryIfSent(draft);
      }
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
    const originThreadId = shell.activeIdeThreadId;
    // Capture attachments before specialty route swaps the thread image scope.
    const attachmentFiles = composerImages.value.map((image) => image.file);
    // Deterministic specialty route only on the send path. Model tie-break runs a
    // full ask-mode composer call (up to 45s) and was blocking Enter/send before
    // the real agent run started.
    const roster = shell.companyEmployeesForCurrentWorkspace;
    const namedAssign = matchNamedAssignEmployee(submitDraft, roster);
    const routeDecision = await resolveEmployeeSpecialtyRoute({
      prompt: submitDraft,
      workspaceId,
      currentEmployee: shell.activeIdeEmployeeRecord,
      roster,
      useModelTiebreak: false,
    });
    const routed = await maybeApplySpecialtyRoute(routeDecision);
    const shouldRewriteNamedAssign =
      Boolean(namedAssign) &&
      (routed ||
        (routeDecision.reason === 'already_owning' &&
          routeDecision.employee?.employee_id === namedAssign?.employee.employee_id));
    const routedPrompt =
      shouldRewriteNamedAssign && namedAssign
        ? rewriteNamedAssignPrompt(submitDraft, namedAssign.employee.name)
        : submitDraft;

    // Clear both the visible draft and its origin-thread copy before dispatch.
    // Waiting for the response let a thread route restore the old prompt after work started.
    shell.ideComposerDraft = '';
    if (originThreadId && workspaceId) {
      persistIdeComposerDraft(workspaceId, '', originThreadId);
    }
    const submitted = await shell.submitIdeComposer(modeForSubmit, {
      attachmentFiles,
      contentOverride: routedPrompt,
    });
    if (!submitted) {
      if (originThreadId && shell.activeIdeThreadId !== originThreadId) {
        await shell.selectIdeThread(originThreadId);
      }
      shell.ideComposerDraft = submitDraft;
      return;
    }
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
    const attachmentFiles = composerImages.value.map((image) => image.file);
    const submitted = await shell.submitIdeComposer('plan', {
      attachmentFiles,
      contentOverride: pending,
    });
    if (!submitted) {
      shell.ideComposerDraft = pending;
      return;
    }
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
    dismissEmployeeSpecialtyRoute();
    const workspaceId = shell.currentWorkspace?.workspace_id ?? '';
    const originThreadId = shell.activeIdeThreadId;
    const attachmentFiles = composerImages.value.map((image) => image.file);
    const roster = shell.companyEmployeesForCurrentWorkspace;
    const namedAssign = matchNamedAssignEmployee(pending, roster);
    const routeDecision = await resolveEmployeeSpecialtyRoute({
      prompt: pending,
      workspaceId,
      currentEmployee: shell.activeIdeEmployeeRecord,
      roster,
      useModelTiebreak: false,
    });
    const routed = await maybeApplySpecialtyRoute(routeDecision);
    const shouldRewriteNamedAssign =
      Boolean(namedAssign) &&
      (routed ||
        (routeDecision.reason === 'already_owning' &&
          routeDecision.employee?.employee_id === namedAssign?.employee.employee_id));
    const routedPrompt =
      shouldRewriteNamedAssign && namedAssign
        ? rewriteNamedAssignPrompt(pending, namedAssign.employee.name)
        : pending;
    const submitted = await shell.submitIdeComposer('agent', {
      attachmentFiles,
      contentOverride: routedPrompt,
    });
    if (!submitted) {
      if (originThreadId && shell.activeIdeThreadId !== originThreadId) {
        await shell.selectIdeThread(originThreadId);
      }
      shell.ideComposerDraft = pending;
      return;
    }
    if (routed && originThreadId && workspaceId) {
      persistIdeComposerDraft(workspaceId, '', originThreadId);
    }
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

    if (shouldProceedDebugReproduceComposer(event, debugReproduceActive())) {
      event.preventDefault();
      const messageId = activeDebugReproduceMessageId();
      if (messageId) {
        void handleDebugReproduceProceed(messageId);
      }
      return;
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
