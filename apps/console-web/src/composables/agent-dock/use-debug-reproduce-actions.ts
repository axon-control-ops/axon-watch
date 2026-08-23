import type { Ref } from 'vue';

import type { ComposerClipboardImage } from '../../lib/composer-clipboard-paste';
import {
  activeDebugReproduceMessageId as resolveActiveDebugReproduceMessageId,
  isDebugReproduceComposerActive,
} from '../../lib/debug-reproduce-composer';
import {
  buildDebugReproduceProceedContent,
  buildDebugReproduceResolvedContent,
} from '../../lib/debug-reproduce-view';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';

type ShellStore = ReturnType<typeof useShellStore>;

export function useDebugReproduceActions(input: {
  shell: ShellStore;
  composerMode: Ref<ComposerMode>;
  composerImages: Ref<ComposerClipboardImage[]>;
  dismissedDebugReproduceMessageId: Ref<string | null>;
  recordComposerHistoryIfSent: (draft: string) => void;
  onDebugReproduceProceed?: (messageId: string) => void;
  withSkillTokensForSubmit?: (draft: string) => string;
  clearSkillAttachments?: () => void;
}) {
  const {
    shell,
    composerMode,
    composerImages,
    dismissedDebugReproduceMessageId,
    recordComposerHistoryIfSent,
    onDebugReproduceProceed,
    withSkillTokensForSubmit,
    clearSkillAttachments,
  } = input;

  function threadDebugMessages() {
    return shell.threadMessages.map((message) => ({
      message_id: message.message_id,
      role: message.role,
      content: message.content,
    }));
  }

  function debugReproduceActive(): boolean {
    return isDebugReproduceComposerActive({
      messages: threadDebugMessages(),
      streaming: shell.agentStreamActive,
      composerMode: composerMode.value,
      linkedRunMode: shell.ideAgentLinkedRun?.mode,
      dismissedMessageId: dismissedDebugReproduceMessageId.value,
    });
  }

  function activeDebugReproduceMessageId(): string | null {
    return resolveActiveDebugReproduceMessageId({
      messages: threadDebugMessages(),
      streaming: shell.agentStreamActive,
    });
  }

  async function submitDebugReproduceFollowUp(
    messageId: string,
    content: string,
  ): Promise<void> {
    if (composerMode.value !== 'debug' && shell.ideAgentLinkedRun?.mode !== 'debug') {
      composerMode.value = 'debug';
    }
    const attachmentFiles = composerImages.value.map((image) => image.file);
    onDebugReproduceProceed?.(messageId);
    const submitted = await shell.submitIdeComposer('debug', {
      contentOverride: content,
      attachmentFiles,
    });
    if (submitted !== false) {
      const operatorReply =
        withSkillTokensForSubmit?.(shell.ideComposerDraft) ?? shell.ideComposerDraft;
      recordComposerHistoryIfSent(operatorReply.trim() || content);
      clearSkillAttachments?.();
    }
  }

  async function handleDebugReproduceProceed(messageId: string): Promise<void> {
    const operatorReply =
      withSkillTokensForSubmit?.(shell.ideComposerDraft) ?? shell.ideComposerDraft;
    await submitDebugReproduceFollowUp(
      messageId,
      buildDebugReproduceProceedContent(operatorReply),
    );
  }

  async function handleDebugReproduceResolved(messageId: string): Promise<void> {
    const operatorReply =
      withSkillTokensForSubmit?.(shell.ideComposerDraft) ?? shell.ideComposerDraft;
    await submitDebugReproduceFollowUp(
      messageId,
      buildDebugReproduceResolvedContent(operatorReply),
    );
  }

  return {
    debugReproduceActive,
    activeDebugReproduceMessageId,
    handleDebugReproduceProceed,
    handleDebugReproduceResolved,
  };
}
