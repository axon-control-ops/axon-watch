import type { Ref } from 'vue';

import type { KairoConverseAnswerTier } from '../../lib/kairo-converse-client';
import type { KairoVoiceCaptureMode } from '../../lib/kairo-voice-gate';
import { normalizeKairoCopy } from '../../lib/kairo-entity-labels';
import {
  formatConversationDisplayReply,
  sanitizeSpokenReply,
} from '../../lib/sanitize-spoken-reply';
import {
  finalizeKairoVoiceFollowupWindow,
  scheduleKairoVoiceFollowupWindowAfterSpeech,
} from '../../lib/kairo-voice-followup-window';
import { useShellStore } from '../../stores/shell';
import {
  mentionsBriefingSurfaceOffer,
  scheduleBriefingSurfaceOffer,
} from './conversation-briefing-surface';
import { kairoConversationReply } from './kairo-conversation-state';
import {
  RUNTIME_ASSISTANT_CUE_COPY,
  RUNTIME_ASSISTANT_CUE_LINE,
  shouldPrimeRuntimeAssistantCue,
} from './runtime-assistant-heuristics';
import { brainGalaxyConversationFocus } from '../brain-galaxy/brain-galaxy-focus';

type ShellStore = ReturnType<typeof useShellStore>;

const RUNTIME_ASSISTANT_CUE_DELAY_MS = 1200;

export function createKairoRuntimeAssistantCue(input: {
  shell: ShellStore;
  pending: Ref<boolean>;
}) {
  let runtimeCueTimer: ReturnType<typeof globalThis.setTimeout> | null = null;

  function clearRuntimeAssistantCue(): void {
    if (runtimeCueTimer !== null) {
      globalThis.clearTimeout(runtimeCueTimer);
      runtimeCueTimer = null;
    }
  }

  function scheduleRuntimeAssistantCue(content: string): void {
    clearRuntimeAssistantCue();
    if (!shouldPrimeRuntimeAssistantCue(content)) {
      return;
    }
    kairoConversationReply.value = RUNTIME_ASSISTANT_CUE_COPY;
    runtimeCueTimer = globalThis.setTimeout(() => {
      runtimeCueTimer = null;
      if (!input.pending.value) {
        return;
      }
      kairoConversationReply.value = RUNTIME_ASSISTANT_CUE_COPY;
      void input.shell.speakKairoConversationLine(RUNTIME_ASSISTANT_CUE_LINE, { operatorPrompt: content });
    }, RUNTIME_ASSISTANT_CUE_DELAY_MS);
  }

  function determineAnswerTier(content: string): KairoConverseAnswerTier {
    return shouldPrimeRuntimeAssistantCue(content) ? 'deep' : 'fast';
  }

  function thinkingStatusLine(content: string, answerTier: KairoConverseAnswerTier): string {
    if (answerTier === 'deep') {
      return 'Consulting runtime context and shaping a short spoken answer…';
    }
    if (brainGalaxyConversationFocus.value?.signalId) {
      return 'Checking the selected signal against the current fleet state…';
    }
    if (/\b(approval|attention|signal|status|briefing|health)\b/i.test(content)) {
      return 'Scanning live system state and briefing signals…';
    }
    return 'Checking the current system state…';
  }

  return {
    clearRuntimeAssistantCue,
    scheduleRuntimeAssistantCue,
    determineAnswerTier,
    thinkingStatusLine,
  };
}

export function createKairoVoiceDelivery(input: {
  shell: ShellStore;
  speakReply: (line: string, operatorPrompt?: string) => Promise<void>;
}) {
  function shouldScheduleHandsFreeFollowup(voiceCaptureMode?: KairoVoiceCaptureMode): boolean {
    return (
      input.shell.operatorPresenceSettings.hands_free_enabled === true &&
      voiceCaptureMode === 'hands_free'
    );
  }

  async function deliverVoiceReply(
    reply: string,
    voiceCaptureMode?: KairoVoiceCaptureMode,
  ): Promise<void> {
    const displayReply = formatConversationDisplayReply(reply);
    const spokenReply = sanitizeSpokenReply(reply);
    kairoConversationReply.value = normalizeKairoCopy(displayReply || spokenReply);
    if (mentionsBriefingSurfaceOffer(displayReply || spokenReply || reply)) {
      scheduleBriefingSurfaceOffer();
    }
    if (shouldScheduleHandsFreeFollowup(voiceCaptureMode)) {
      scheduleKairoVoiceFollowupWindowAfterSpeech();
    }
    await input.speakReply(spokenReply || kairoConversationReply.value);
    finalizeKairoVoiceFollowupWindow();
  }

  return { deliverVoiceReply };
}
