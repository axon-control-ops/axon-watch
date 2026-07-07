import { computed, ref } from 'vue';

import { postKairoConverse } from '../../lib/kairo-converse-client';
import { enqueueSpeech } from '../../lib/speech-queue';
import { useShellStore } from '../../stores/shell';
import { resolveConversationNavigationIntent } from './conversation-intents';
import {
  kairoConversationError,
  kairoConversationPhase,
  kairoConversationReply,
  setKairoConversationPhase,
} from './kairo-conversation-state';

export function useKairoConversation() {
  const shell = useShellStore();
  const draft = ref('');
  const pending = ref(false);

  const canSubmit = computed(() => draft.value.trim().length > 0 && !pending.value);
  const workspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? '');

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

  function speakReply(line: string): void {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }
    const blocked =
      shell.operatorPresenceSettings.privacy_mode ||
      shell.operatorPresenceSettings.kairo_narration === 'off' ||
      !shell.operatorPresenceSettings.spoken_alerts_enabled;
    if (blocked || typeof window === 'undefined' || !window.speechSynthesis) {
      return;
    }
    setKairoConversationPhase('speaking');
    enqueueSpeech(trimmed, window.speechSynthesis);
    window.setTimeout(() => setKairoConversationPhase('idle'), Math.max(1200, trimmed.length * 45));
  }

  async function submitTurn(rawContent?: string): Promise<void> {
    const content = (rawContent ?? draft.value).trim();
    if (!content || pending.value) {
      return;
    }

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
      return;
    }

    try {
      const response = await postKairoConverse({
        content,
        session_id: kairoSpeechSessionId(),
        workspace_id: workspaceId.value,
        use_runtime: false,
      });
      kairoConversationReply.value = response.reply;
      draft.value = '';
      speakReply(response.reply);

      if (response.turn_kind === 'command' && response.command_content) {
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
    setKairoConversationPhase('listening');
  }

  function handleBlur(): void {
    if (kairoConversationPhase.value === 'listening') {
      setKairoConversationPhase('idle');
    }
  }

  return {
    draft,
    pending,
    canSubmit,
    submitTurn,
    handleFocus,
    handleBlur,
  };
}
