import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { subscribeKairoVoiceChunk } from '../../lib/kairo-voice-playback';
import {
  subscribeKairoVoiceUtterance,
  type KairoVoiceSpeaker,
} from '../../lib/kairo-voice-utterance';
import { stripAgentStreamFenceMarkers } from '../../lib/agent-live-line-view';
import { useShellStore } from '../../stores/shell';
import { resolveGalaxySpeakerAvatar } from './galaxy-speaker-avatar-view';
import {
  buildNarrationSentenceSteps,
  GALAXY_CAPTION_FLOAT_MS,
  GALAXY_CAPTION_MAX_VISIBLE,
  type GalaxySpeechCaption,
} from './galaxy-speech-captions-view';

let nextCaptionId = 0;

export function useGalaxySpeechCaptions() {
  const shell = useShellStore();
  const captions = ref<GalaxySpeechCaption[]>([]);
  const activeSpeaker = ref<KairoVoiceSpeaker | null>(null);
  const activeUtteranceText = ref<string | null>(null);
  const timers: number[] = [];
  let unsubscribeUtterance: (() => void) | null = null;
  let unsubscribeChunk: (() => void) | null = null;
  let generation = 0;
  let utteranceActive = false;

  const workspaceLabelById = computed(() => {
    const map: Record<string, string> = {};
    for (const workspace of shell.workspaces) {
      map[workspace.workspace_id] =
        workspace.display_name?.trim() || workspace.workspace_id;
    }
    return map;
  });

  const activityLine = computed(() => {
    const spoken = activeUtteranceText.value?.trim() || null;
    if (spoken) {
      return spoken.length > 120 ? `${spoken.slice(0, 117)}…` : spoken;
    }
    const activity = shell.ideComposerActivity;
    if (!activity) {
      return null;
    }
    const live = activity.liveBodyFull?.trim() || activity.label?.trim() || null;
    if (!live) {
      return null;
    }
    // Keep the HUD line short.
    return live.length > 120 ? `${live.slice(0, 117)}…` : live;
  });

  const speakerAvatar = computed(() =>
    resolveGalaxySpeakerAvatar(activeSpeaker.value, shell.companyEmployeesFleet, {
      speaking: Boolean(activeSpeaker.value),
      activityLine: activityLine.value,
      workspaceLabelById: workspaceLabelById.value,
      currentWorkspaceId: shell.currentWorkspace?.workspace_id ?? null,
    }),
  );

  function clearTimers(): void {
    for (const timer of timers.splice(0, timers.length)) {
      window.clearTimeout(timer);
    }
  }

  function pruneCaption(id: string): void {
    captions.value = captions.value.filter((caption) => caption.id !== id);
  }

  function pushCaption(text: string, gen: number): void {
    if (gen !== generation || !text.trim()) {
      return;
    }
    const caption: GalaxySpeechCaption = {
      id: `galaxy-cap-${++nextCaptionId}`,
      text: text.trim(),
      bornAt: Date.now(),
    };
    captions.value = [...captions.value, caption].slice(-GALAXY_CAPTION_MAX_VISIBLE);
    const removeTimer = window.setTimeout(() => {
      pruneCaption(caption.id);
    }, GALAXY_CAPTION_FLOAT_MS);
    timers.push(removeTimer);
  }

  /** Narration chunk started — show its sentences one at a time from this moment. */
  function onNarrationChunk(chunkText: string): void {
    if (!utteranceActive) {
      return;
    }
    clearTimers();
    generation += 1;
    const gen = generation;
    const steps = buildNarrationSentenceSteps(chunkText);
    if (steps.length === 0) {
      return;
    }
    for (const step of steps) {
      if (step.delayMs <= 0) {
        pushCaption(step.phrase, gen);
        continue;
      }
      const timer = window.setTimeout(() => {
        pushCaption(step.phrase, gen);
      }, step.delayMs);
      timers.push(timer);
    }
  }

  function startUtterance(text: string, speaker: KairoVoiceSpeaker | null): void {
    utteranceActive = true;
    activeUtteranceText.value = stripAgentStreamFenceMarkers(text) || null;
    activeSpeaker.value = speaker;
    clearTimers();
    captions.value = [];
    generation += 1;
  }

  function endUtterance(): void {
    utteranceActive = false;
    activeUtteranceText.value = null;
    activeSpeaker.value = null;
    generation += 1;
    clearTimers();
  }

  onMounted(() => {
    unsubscribeUtterance = subscribeKairoVoiceUtterance((state) => {
      if (state.text) {
        startUtterance(state.text, state.speaker);
        return;
      }
      endUtterance();
    });
    unsubscribeChunk = subscribeKairoVoiceChunk((chunkText) => {
      onNarrationChunk(chunkText);
    });
  });

  onBeforeUnmount(() => {
    unsubscribeUtterance?.();
    unsubscribeChunk?.();
    unsubscribeUtterance = null;
    unsubscribeChunk = null;
    clearTimers();
    captions.value = [];
    activeUtteranceText.value = null;
    activeSpeaker.value = null;
  });

  return { captions, speakerAvatar, layoutMode: computed(() => shell.layoutMode) };
}
