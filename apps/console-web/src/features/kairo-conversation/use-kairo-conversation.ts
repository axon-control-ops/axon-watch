import { computed, ref } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { useShellStore } from '../../stores/shell';
import { resolveConversationNavigationIntent } from './conversation-intents';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';
import { useKairoSpeechCapture } from './use-kairo-speech-capture';

const HANDOFF_CLIENT_RE = /\b(hand\s*off|handoff|continue in ide|investigate in ide)\b/i;

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);

  const canSubmit = computed(() => draft.value.trim().length > 0 && !pending.value);
  const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

  const speechCapture = useKairoSpeechCapture({
    privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
    onFinalTranscript: async (transcript) => {
      draft.value = transcript;
      await submitTurn(transcript);
    },
  });

  function kairoSpeechSessionId(): string {
    const key = 'axon-x:kairo-speech-session';
    if (typeof sessionStorage === 'undefined') {
      return 'default';
    }
    let id = sessionStorage.getItem(key);
    if (!id) {
      id = `kairo-${Date.now()}`;
      sessionStorage.setItem(key, id);
    }
    return id;
  }

  function speakReply(line: string, operatorPrompt?: string): void {
    shell.interruptKairoVoice();
    void shell.speakKairoConversationLine(line, { operatorPrompt });
  }

  async function executeConverseAction(
    action: NonNullable<Awaited<ReturnType<typeof postKairoConverse>>['action']>,
  ): Promise<void> {
    if (action.type === 'handoff_signal') {
      await shell.handoffSignalToIde({
        signal_id: action.signal_id,
        workspace_id: action.target_workspace_id,
        title: action.task.replace(/^Investigate signal "/, '').split('"')[0] ?? action.task,
        summary: action.task,
      });
      return;
    }
    if (action.type === 'dispatch_command') {
      await shell.submitOperatorCommandContent(action.content);
    }
  }

  async function tryClientHandoff(content: string): Promise<boolean> {
    if (!HANDOFF_CLIENT_RE.test(content)) {
      return false;
    }
    const topSignal = shell.operatorBriefing?.top_signals[0];
    if (!topSignal) {
      kairoConversationReply.value = 'No signal in context to hand off yet.';
      speakReply(kairoConversationReply.value);
      return true;
    }
    await shell.handoffSignalToIde({
      signal_id: topSignal.signal_id,
      workspace_id: topSignal.workspace_id,
      title: topSignal.title,
      summary: topSignal.summary,
    });
    kairoConversationReply.value = 'Handing the top signal off to the IDE.';
    speakReply(kairoConversationReply.value);
    return true;
  }

  async function submitTurn(rawContent?: string): Promise<void> {
    const content = (rawContent ?? draft.value).trim();
    if (!content || pending.value) {
      return;
    }

    shell.interruptKairoVoice();
    pending.value = true;
    kairoConversationError.value = null;
    setKairoConversationPhase('thinking');

    const navIntent = resolveConversationNavigationIntent(
      content,
      shell.workspaces.map((workspace) => ({
        workspace_id: workspace.workspace_id,
        display_name: workspace.display_name ?? workspace.workspace_id,
      })),
    );

    if (navIntent) {
      if (navIntent.kind === 'focus_attention') {
        shell.focusAttentionSidebar();
      } else if (navIntent.kind === 'focus_workspace' && navIntent.workspaceId) {
        shell.setCurrentWorkspace(navIntent.workspaceId);
      } else if (navIntent.kind === 'switch_center_view' && navIntent.centerView) {
        shell.setOperatorCenterView(navIntent.centerView);
      }
      kairoConversationReply.value = navIntent.reply;
      draft.value = '';
      speakReply(navIntent.reply);
      pending.value = false;
      setKairoConversationPhase('idle');
      return;
    }

    if (await tryClientHandoff(content)) {
      draft.value = '';
      pending.value = false;
      setKairoConversationPhase('idle');
      return;
    }

    try {
      const response = await postKairoConverse({
        content,
        session_id: kairoSpeechSessionId(),
        workspace_id: workspaceId.value,
      });
      kairoConversationReply.value = response.reply;
      draft.value = '';
      speakReply(response.reply, content);

      if (response.action) {
        await executeConverseAction(response.action);
      } else if (response.turn_kind === 'command' && response.command_content) {
        await shell.submitOperatorCommandContent(response.command_content);
      } else if (response.turn_kind === 'action' && response.command_content) {
        await shell.submitOperatorCommandContent(response.command_content);
      }
    } catch (error) {
      kairoConversationError.value =
        error instanceof Error ? error.message : 'KAIRO conversation failed';
      setKairoConversationPhase('idle');
    } finally {
      pending.value = false;
      if (kairoConversationPhase.value === 'thinking') {
        setKairoConversationPhase('idle');
      }
    }
  }

  function handleFocus(): void {
    if (!speechCapture.capturing.value) {
      setKairoConversationPhase('listening');
    }
  }

  function handleBlur(): void {
    if (kairoConversationPhase.value === 'listening' && !speechCapture.capturing.value) {
      setKairoConversationPhase('idle');
    }
  }

  function startVoiceCapture(): boolean {
    shell.interruptKairoVoice();
    return speechCapture.startCapture();
  }

  function stopVoiceCapture(): void {
    speechCapture.stopCapture();
  }

  return {
    draft,
    pending,
    canSubmit,
    submitTurn,
    handleFocus,
    handleBlur,
    speechCapture,
    startVoiceCapture,
    stopVoiceCapture,
  };
}
