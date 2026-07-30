import { computed, nextTick, type Ref } from 'vue';

import { resolveActiveIdeAgentMessage } from '../../lib/ide-agent-center-view';
import {
  summarizeIdeAgentActivity,
  summarizeIdeAgentActivityFromCounts,
} from '../../lib/ide-agent-activity-view';
import { filterMcpToolsForComposerMode } from '../../lib/composer-mcp-tools-view';
import { isToolCapableComposerMode } from '../../lib/composer-tool-modes';
import { plainTextToInstructionsMarkdown } from '../../lib/plain-text-to-instructions';
import {
  extractDebugReproduceRequest,
  shouldShowDebugReproduceBanner,
} from '../../lib/debug-reproduce-view';
import { OPERATOR_PERSONA_NAME } from '../../lib/operator-persona-name';
import { runContinueActionLabel } from '../../lib/run-lifecycle-ui';
import {
  composerAccessBannerCopy,
  composerAccessTone,
} from '../../lib/sandbox-session-view';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerDisplayStateOptions = {
  shell: ShellStore;
  composerMode: Ref<ComposerMode>;
  composerDragOver: Ref<boolean>;
  isFullAccessAgent: Ref<boolean>;
  sandboxSessionEnabled: Ref<boolean>;
  kairoDraft: Ref<string>;
  kairoCanSubmit: Ref<boolean>;
  kairoPending: Ref<boolean>;
  dismissedDebugReproduceMessageId: Ref<string | null>;
  syncComposerHeight: () => void;
  skillAttachmentCount?: Ref<number>;
};

export function useComposerDisplayState(options: UseComposerDisplayStateOptions) {
  const {
    shell,
    composerMode,
    composerDragOver,
    isFullAccessAgent,
    sandboxSessionEnabled,
    kairoDraft,
    kairoCanSubmit,
    kairoPending,
    dismissedDebugReproduceMessageId,
    syncComposerHeight,
    skillAttachmentCount,
  } = options;

  const composerAgentBusy = computed(() => shell.composerAgentBusy);
  const debugReproduceRequest = computed(() =>
    extractDebugReproduceRequest({
      messages: shell.threadMessages.map((message) => ({
        message_id: message.message_id,
        role: message.role,
        content: message.content,
      })),
      streaming: shell.agentStreamActive,
    }),
  );
  const showDebugReproduceBanner = computed(() =>
    shouldShowDebugReproduceBanner({
      composerMode: composerMode.value,
      linkedRunMode: shell.ideAgentLinkedRun?.mode,
      request: debugReproduceRequest.value,
      dismissedMessageId: dismissedDebugReproduceMessageId.value,
    }),
  );

  function handleDebugReproduceDismiss(): void {
    dismissedDebugReproduceMessageId.value = debugReproduceRequest.value?.messageId ?? null;
  }

  const composerPlaceholder = computed(() => {
    if (composerMode.value === 'kairo') {
      return `Talk to ${OPERATOR_PERSONA_NAME} — answers are spoken aloud`;
    }
    if (composerAgentBusy.value && isToolCapableComposerMode(composerMode.value)) {
      return sandboxSessionEnabled.value
        ? 'Queue a Sandbox follow-up or steer with Ctrl+Enter…'
        : 'Queue a follow-up or steer with Ctrl+Enter…';
    }
    if (composerMode.value === 'plan') {
      return sandboxSessionEnabled.value
        ? 'Plan Sandbox changes, constraints, and verification…'
        : 'Plan your approach, constraints, and verification path…';
    }
    if (composerMode.value === 'ask') {
      return 'Ask about this workspace, file, or runtime…';
    }
    if (composerMode.value === 'debug') {
      return sandboxSessionEnabled.value
        ? 'Debug in Sandbox — describe expected vs actual and how to reproduce…'
        : 'Describe the bug, expected vs actual, and how to reproduce…';
    }
    if (sandboxSessionEnabled.value) {
      return 'Describe Sandbox changes — edits stay in the disposable session…';
    }
    return 'Describe what you want to build or change…';
  });

  const composerAccessBanner = computed(() =>
    composerAccessBannerCopy({
      fullAccess: isFullAccessAgent.value,
      sandboxEnabled: sandboxSessionEnabled.value,
    }),
  );

  const composerAccessToneValue = computed(() =>
    composerAccessTone({
      fullAccess: isFullAccessAgent.value,
      sandboxEnabled: sandboxSessionEnabled.value,
    }),
  );

  const mcpToolsForMode = computed(() => {
    if (composerMode.value === 'kairo') {
      return [];
    }
    return filterMcpToolsForComposerMode(shell.runtimeMcpTools, composerMode.value);
  });

  const showComposerResume = computed(() => shell.canResumeIdeAgentRun);
  const composerResumeLabel = computed(() =>
    runContinueActionLabel({
      phase: shell.ideAgentLinkedRun?.phase,
      agentStreamActive: shell.agentStreamActive,
      mode: shell.ideAgentLinkedRun?.mode,
      pending: shell.runMutationState === 'resuming',
      continueLabel: 'Continue',
      resumeLabel: 'Resume',
      pendingLabel: 'Resuming…',
    }),
  );
  const showComposerStop = computed(
    () => shell.canStopIdeAgentRun && composerMode.value !== 'kairo',
  );
  const showComposerSteer = computed(
    () =>
      composerAgentBusy.value
      && isToolCapableComposerMode(composerMode.value)
      && Boolean(shell.ideComposerDraft.trim()),
  );
  const composerQueueHint = computed(() => {
    if (!composerAgentBusy.value || !isToolCapableComposerMode(composerMode.value)) {
      return '';
    }
    if (!shell.ideComposerDraft.trim()) {
      return '';
    }
    const steerKey = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform)
      ? '⌘'
      : 'Ctrl';
    return `Enter queues · ↑ steers now · ${steerKey}+Enter steers`;
  });
  const composerActivitySummary = computed(() => {
    if (!shell.agentStreamActive && !shell.composerAgentBusy) {
      return null;
    }
    const message = resolveActiveIdeAgentMessage(
      shell.threadMessages,
      shell.agentStreamActive,
      shell.agentStreamMessageId,
    );
    if (!message) {
      return null;
    }
    const streamCounts = shell.ideComposerActivity?.streamCounts;
    if (streamCounts) {
      return summarizeIdeAgentActivityFromCounts(streamCounts);
    }
    return summarizeIdeAgentActivity(message.content);
  });
  const composerActivityChips = computed(() =>
    composerMode.value === 'kairo' ? [] : composerActivitySummary.value?.chips ?? [],
  );
  const composerDraftModel = computed({
    get: () => (composerMode.value === 'kairo' ? kairoDraft.value : shell.ideComposerDraft),
    set: (value: string) => {
      if (composerMode.value === 'kairo') {
        kairoDraft.value = value;
        return;
      }
      if (shell.commandMutationError && value !== shell.ideComposerDraft) {
        shell.commandMutationError = null;
      }
      shell.ideComposerDraft = value;
    },
  });
  const canConvertInstructions = computed(() => Boolean(composerDraftModel.value.trim()));

  function convertDraftToInstructions(): void {
    const next = plainTextToInstructionsMarkdown(composerDraftModel.value);
    composerDraftModel.value = next;
    void nextTick(syncComposerHeight);
  }

  const canSubmitComposer = computed(() => {
    if (composerMode.value === 'kairo') {
      return kairoCanSubmit.value && Boolean(shell.currentWorkspace);
    }
    if (shell.canSubmitIdeComposer) {
      return true;
    }
    return (
      shell.commandMutationState !== 'submitting' &&
      Boolean(shell.currentWorkspace?.workspace_id) &&
      (skillAttachmentCount?.value ?? 0) > 0
    );
  });

  const composerSubmitLabel = computed(() => {
    if (composerMode.value === 'kairo') {
      return kairoPending.value ? `Asking ${OPERATOR_PERSONA_NAME}` : `Ask ${OPERATOR_PERSONA_NAME}`;
    }
    if (shell.commandMutationState === 'submitting') {
      return sandboxSessionEnabled.value ? 'Sending in Sandbox' : 'Sending command';
    }
    if (composerAgentBusy.value && isToolCapableComposerMode(composerMode.value)) {
      return sandboxSessionEnabled.value ? 'Queue Sandbox' : 'Queue message';
    }
    return sandboxSessionEnabled.value ? 'Send in Sandbox' : 'Send command';
  });

  const composerShellClasses = computed(() => ({
    [`agent-dock-composer__shell--${composerMode.value}`]: true,
    'agent-dock-composer__shell--full-access':
      isFullAccessAgent.value && !sandboxSessionEnabled.value,
    'agent-dock-composer__shell--sandbox':
      sandboxSessionEnabled.value && !isFullAccessAgent.value,
    'agent-dock-composer__shell--sandbox-full':
      sandboxSessionEnabled.value && isFullAccessAgent.value,
    'agent-dock-composer__shell--drag-over': composerDragOver.value,
  }));

  return {
    composerAccessBanner,
    composerAccessToneValue,
    composerActivityChips,
    composerDraftModel,
    canConvertInstructions,
    convertDraftToInstructions,
    composerPlaceholder,
    composerQueueHint,
    composerResumeLabel,
    composerShellClasses,
    composerSubmitLabel,
    canSubmitComposer,
    debugReproduceRequest,
    handleDebugReproduceDismiss,
    mcpToolsForMode,
    showComposerResume,
    showComposerSteer,
    showComposerStop,
    showDebugReproduceBanner,
  };
}
