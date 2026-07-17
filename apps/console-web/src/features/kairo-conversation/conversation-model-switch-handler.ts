import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import type { useShellStore } from '../../stores/shell';
import { applyBrainModelSwitch } from './apply-brain-model-switch';
import { resolveConversationModelSwitchIntent } from './conversation-model-intents';

type ShellStore = ReturnType<typeof useShellStore>;

export async function handleConversationModelSwitchIntent(input: {
  shell: ShellStore;
  content: string;
  voiceCaptureMode?: KairoVoiceCaptureMode;
  clearRuntimeAssistantCue: () => void;
  deliverVoiceReply: (line: string, voiceCaptureMode?: KairoVoiceCaptureMode) => Promise<void>;
  resetDraftState: () => void;
}): Promise<boolean> {
  const modelIntent = resolveConversationModelSwitchIntent(
    input.content,
    input.shell.cursorCatalogRows,
  );
  if (!modelIntent) {
    return false;
  }

  input.clearRuntimeAssistantCue();
  input.resetDraftState();
  if (!modelIntent.modelId) {
    await input.deliverVoiceReply(modelIntent.reply, input.voiceCaptureMode);
    return true;
  }
  if (
    !applyBrainModelSwitch(input.shell, {
      modelId: modelIntent.modelId,
      rows: input.shell.cursorCatalogRows,
    })
  ) {
    await input.deliverVoiceReply(
      'Select a workspace first, then I can switch the brain model.',
      input.voiceCaptureMode,
    );
    return true;
  }
  await input.deliverVoiceReply(modelIntent.reply, input.voiceCaptureMode);
  return true;
}
