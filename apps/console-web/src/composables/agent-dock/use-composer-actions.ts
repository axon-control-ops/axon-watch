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
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';

type ShellStore = ReturnType<typeof useShellStore>;

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

  function handleBackgroundRun(): void {
    shell.backgroundIdeAgentRun();
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
      return;
    }
    if (composerMode.value === 'kairo') {
      await submitKairoTurn(draft);
      return;
    }
    const attachmentFiles = composerImages.value.map((image) => image.file);
    await shell.submitIdeComposer(composerMode.value, { attachmentFiles });
    recordComposerHistoryIfSent(draft);
  }

  async function handleSteer(event?: Event): Promise<void> {
    event?.preventDefault();
    if (composerMode.value === 'kairo') {
      return;
    }
    const draft = shell.ideComposerDraft.trim();
    const attachmentFiles = composerImages.value.map((image) => image.file);
    await shell.steerIdeComposer(composerMode.value, { attachmentFiles });
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

  function revealComposerTerminalPanel(): void {
    shell.revealIdeTerminalPanel();
  }

  function handleComposerKeydown(event: KeyboardEvent): void {
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
    handleApproveRun,
    handleBackgroundRun,
    handleComposerKeydown,
    handleRejectRun,
    handleResumeRun,
    handleSteer,
    handleSteerQueuedMessage,
    handleStopRun,
    handleSubmit,
    removeQueuedMessage,
    revealComposerTerminalPanel,
    toggleVoiceCapture,
  };
}
