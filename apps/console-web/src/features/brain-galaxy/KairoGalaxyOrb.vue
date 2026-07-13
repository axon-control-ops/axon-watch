<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import {
  galaxyOrbBeads,
  galaxyOrbHint,
  galaxyOrbModeClass,
  galaxyOrbModeLabel,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbStatusLabel,
  galaxyOrbTicks,
} from './kairo-galaxy-orb-view';
import { resolveOrbPointerUpIntent } from './kairo-galaxy-orb-interaction';
import { rectsOverlap, resolveAutoAvoidOrbCandidates } from './kairo-galaxy-orb-position';
import { kairoPresenceModuleParts } from '../../lib/mockup-shell-view';
import { resolveKairoPresenceState } from '../../lib/kairo-presence';
import { clearKairoVoiceFollowupWindow } from '../../lib/kairo-voice-followup-window';
import { subscribeKairoVoiceChunk, subscribeKairoVoiceSpeaking } from '../../lib/kairo-voice-playback';
import { kairoConversationPhase, isKairoConversationBusy, kairoConversationReply, setKairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';
import { useKairoSpeechCapture } from '../kairo-conversation/use-kairo-speech-capture';
import { OPERATOR_PERSONA_NAME, OPERATOR_PERSONA_ORB_LABEL } from '../../lib/operator-persona-name';
import { useShellStore } from '../../stores/shell';

const personaOrbLabel = OPERATOR_PERSONA_ORB_LABEL;
const personaName = OPERATOR_PERSONA_NAME;

const HOLD_TO_TALK_MS = 280;
const ORB_DRAG_STORAGE_KEY = 'axon-x:vaxon-orb-position';
const ORB_MARGIN_LEFT_PX = 12;
const ORB_MARGIN_TOP_PX = 56;
const ORB_MARGIN_RIGHT_PX = 12;
const ORB_MARGIN_BOTTOM_PX = 94;
const ORB_REPLY_CLEARANCE_PX = 12;
const ORB_TOP_DOCK_OFFSET_PX = 48;

const shell = useShellStore();
const kairoSpeaking = ref(false);
const voiceBeat = ref(false);
const orbAnchor = ref<HTMLElement | null>(null);
const orbPosition = ref<{ x: number; y: number } | null>(null);
const orbDragging = ref(false);
let holdTimer: number | null = null;
let pointerDownAt = 0;
let suppressModeToggleClick = false;
let dragPointerId: number | null = null;
let dragOrigin: { x: number; y: number } | null = null;
let dragStartPointer: { x: number; y: number } | null = null;
let orbUserPositioned = false;
let orbAutoAvoidActive = false;
let bottomHudObserver: ResizeObserver | null = null;
let voiceBeatTimer: number | null = null;
const handleWindowResize = (): void => {
  syncOrbPosition(false);
  resolveOrbOverlap();
};

const ticks = galaxyOrbTicks();
const beads = galaxyOrbBeads();

const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);

const handsFreeEnabled = computed(
  () => shell.operatorPresenceSettings.hands_free_enabled === true,
);

const presenceState = computed(() => {
  const highSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0;
  const criticalSignals =
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'critical').length ??
    0;
  return resolveKairoPresenceState({
    pendingApprovals: pendingApprovals.value,
    criticalSignals,
    highSignals,
    watchConnected: shell.runtimeSummary?.watch.connected ?? false,
    runtimeLoaded: shell.runtimeSummaryLoadState === 'loaded',
    privacyBlocked: shell.operatorPresenceSettings.privacy_mode,
  });
});

const parts = computed(() => kairoPresenceModuleParts(presenceState.value));

const orbStateClass = computed(() =>
  galaxyOrbStateClass(
    presenceState.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
    kairoConversationPhase.value,
  ),
);

const orbModeClass = computed(() => galaxyOrbModeClass(handsFreeEnabled.value));

const modelLabel = computed(() => galaxyOrbModelLabel(shell.selectedComposerModel));

const hint = computed(() =>
  galaxyOrbHint(
    presenceState.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
    kairoConversationPhase.value,
    handsFreeEnabled.value,
  ),
);

const modeLabel = computed(() =>
  galaxyOrbModeLabel(handsFreeEnabled.value, kairoConversationPhase.value),
);

const orbStatusLabel = computed(() =>
  galaxyOrbStatusLabel(
    kairoConversationPhase.value,
    kairoSpeaking.value || shell.kairoSpeechActive,
  ),
);

const orbBusy = computed(() => isKairoConversationBusy());

const showInterrupt = computed(
  () => shell.kairoSpeechActive || kairoConversationPhase.value === 'thinking',
);

const orbAnchorStyle = computed(() => {
  if (!orbPosition.value) {
    return undefined;
  }
  return {
    left: `${orbPosition.value.x}px`,
    top: `${orbPosition.value.y}px`,
  };
});

function handleInterrupt(): void {
  shell.interruptKairoVoice();
  clearKairoVoiceFollowupWindow();
  setKairoConversationPhase('idle');
}

const voiceBlocked = computed(() => shell.operatorPresenceSettings.privacy_mode);

const speechCapture = useKairoSpeechCapture({
  privacyBlocked: () => shell.operatorPresenceSettings.privacy_mode,
  captureMode: 'manual',
  stopOnUnmount: 'manual_only',
});

function stageElement(): HTMLElement | null {
  return orbAnchor.value?.closest('.brain-galaxy-stage') as HTMLElement | null;
}

function bottomHudElement(): HTMLElement | null {
  return stageElement()?.querySelector('.brain-galaxy-stage__hud--bottom') ?? null;
}

function orbOverlapsBottomHud(): boolean {
  const anchor = orbAnchor.value;
  const hud = bottomHudElement();
  if (!anchor || !hud) {
    return false;
  }
  return rectsOverlap(anchor.getBoundingClientRect(), hud.getBoundingClientRect());
}

function clampOrbPosition(position: { x: number; y: number }): { x: number; y: number } {
  const stage = stageElement();
  const anchor = orbAnchor.value;
  if (!stage || !anchor) {
    return position;
  }
  const maxX = Math.max(ORB_MARGIN_LEFT_PX, stage.clientWidth - anchor.offsetWidth - ORB_MARGIN_RIGHT_PX);
  const maxY = Math.max(ORB_MARGIN_TOP_PX, stage.clientHeight - anchor.offsetHeight - ORB_MARGIN_BOTTOM_PX);
  return {
    x: Math.min(Math.max(position.x, ORB_MARGIN_LEFT_PX), maxX),
    y: Math.min(Math.max(position.y, ORB_MARGIN_TOP_PX), maxY),
  };
}

function persistOrbPosition(): void {
  if (!orbPosition.value || typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(ORB_DRAG_STORAGE_KEY, JSON.stringify(orbPosition.value));
}

function restoreOrbPosition(): { x: number; y: number } | null {
  if (typeof localStorage === 'undefined') {
    return null;
  }
  try {
    const raw = localStorage.getItem(ORB_DRAG_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { x?: unknown; y?: unknown };
    if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
      return { x: parsed.x, y: parsed.y };
    }
  } catch {
    // Ignore malformed saved positions and fall back to the default docked spot.
  }
  return null;
}

function defaultOrbPosition(): { x: number; y: number } | null {
  const stage = stageElement();
  const anchor = orbAnchor.value;
  if (!stage || !anchor) {
    return null;
  }
  return clampOrbPosition({
    x: stage.clientWidth - anchor.offsetWidth - ORB_MARGIN_RIGHT_PX,
    y: stage.clientHeight - anchor.offsetHeight - ORB_MARGIN_BOTTOM_PX,
  });
}

function applyOrbReplyAvoidPosition(): void {
  const stage = stageElement();
  const anchor = orbAnchor.value;
  const hud = bottomHudElement();
  if (!stage || !anchor) {
    return;
  }
  if (!hud) {
    return;
  }
  const stageRect = stage.getBoundingClientRect();
  const hudRect = hud.getBoundingClientRect();
  const candidates = resolveAutoAvoidOrbCandidates({
    stage: {
      width: stage.clientWidth,
      height: stage.clientHeight,
    },
    orb: {
      width: anchor.offsetWidth,
      height: anchor.offsetHeight,
    },
    obstacle: {
      left: hudRect.left - stageRect.left,
      top: hudRect.top - stageRect.top,
      right: hudRect.right - stageRect.left,
      bottom: hudRect.bottom - stageRect.top,
    },
    margins: {
      left: ORB_MARGIN_LEFT_PX,
      top: ORB_MARGIN_TOP_PX,
      right: ORB_MARGIN_RIGHT_PX,
      bottom: ORB_MARGIN_BOTTOM_PX,
    },
    dockTopOffset: ORB_TOP_DOCK_OFFSET_PX,
    clearance: ORB_REPLY_CLEARANCE_PX,
  });
  for (const candidate of candidates) {
    orbPosition.value = clampOrbPosition(candidate);
    if (!orbOverlapsBottomHud()) {
      orbAutoAvoidActive = true;
      return;
    }
  }
  orbAutoAvoidActive = true;
}

function resolveOrbOverlap(): void {
  if (orbDragging.value || orbUserPositioned) {
    return;
  }
  void nextTick(() => {
    if (orbDragging.value || orbUserPositioned) {
      return;
    }
    if (orbOverlapsBottomHud()) {
      applyOrbReplyAvoidPosition();
      return;
    }
    if (orbAutoAvoidActive) {
      orbAutoAvoidActive = false;
      syncOrbPosition(true);
    }
  });
}

function attachBottomHudObserver(): void {
  bottomHudObserver?.disconnect();
  const hud = bottomHudElement();
  if (!hud || typeof ResizeObserver === 'undefined') {
    return;
  }
  bottomHudObserver = new ResizeObserver(() => {
    resolveOrbOverlap();
  });
  bottomHudObserver.observe(hud);
}

function syncOrbPosition(initial = false): void {
  const base = (initial ? restoreOrbPosition() : orbPosition.value) ?? defaultOrbPosition();
  if (!base) {
    return;
  }
  orbPosition.value = clampOrbPosition(base);
}

function clearHoldTimer(): void {
  if (holdTimer !== null) {
    window.clearTimeout(holdTimer);
    holdTimer = null;
  }
}

async function toggleHandsFreeMode(): Promise<void> {
  if (voiceBlocked.value) {
    return;
  }
  if (handsFreeEnabled.value && speechCapture.capturing.value) {
    speechCapture.stopCapture();
  }
  await shell.saveOperatorPresenceSettingsPatch({
    hands_free_enabled: !handsFreeEnabled.value,
  });
}

function handleOrbClick(): void {
  if (suppressModeToggleClick) {
    suppressModeToggleClick = false;
    return;
  }
  void toggleHandsFreeMode();
}

function handleOrbPointerDown(event: PointerEvent): void {
  if (voiceBlocked.value || !speechCapture.supported || orbBusy.value) {
    return;
  }
  pointerDownAt = Date.now();
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.setPointerCapture) {
    target.setPointerCapture(event.pointerId);
  }
  if (handsFreeEnabled.value) {
    return;
  }
  clearHoldTimer();
  holdTimer = window.setTimeout(() => {
    holdTimer = null;
    if (!handsFreeEnabled.value) {
      handleOrbPttStart();
    }
  }, HOLD_TO_TALK_MS);
}

function handleOrbPointerUp(event: PointerEvent): void {
  const target = event.currentTarget;
  if (target instanceof HTMLElement && target.releasePointerCapture) {
    try {
      if (target.hasPointerCapture(event.pointerId)) {
        target.releasePointerCapture(event.pointerId);
      }
    } catch {
      // ignore
    }
  }
  clearHoldTimer();
  const heldMs = Date.now() - pointerDownAt;
  const pointerUpResolution = resolveOrbPointerUpIntent({
    captureActive: speechCapture.capturing.value,
    handsFreeEnabled: handsFreeEnabled.value,
    heldMs,
    holdToTalkMs: HOLD_TO_TALK_MS,
  });
  suppressModeToggleClick = pointerUpResolution.suppressToggleClick;
  if (pointerUpResolution.stopCapture) {
    speechCapture.stopCapture();
    return;
  }
}

function handleOrbPttStart(): void {
  if (voiceBlocked.value || !speechCapture.supported || orbBusy.value) {
    return;
  }
  shell.interruptKairoVoice();
  speechCapture.startCapture('manual');
}

function handleOrbDragStart(event: PointerEvent): void {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (orbPosition.value === null) {
    syncOrbPosition(true);
  }
  target.setPointerCapture?.(event.pointerId);
  dragPointerId = event.pointerId;
  dragOrigin = orbPosition.value ? { ...orbPosition.value } : defaultOrbPosition();
  dragStartPointer = { x: event.clientX, y: event.clientY };
  orbDragging.value = true;
}

function handleOrbDragMove(event: PointerEvent): void {
  if (
    dragPointerId === null ||
    event.pointerId !== dragPointerId ||
    !dragOrigin ||
    !dragStartPointer
  ) {
    return;
  }
  orbPosition.value = clampOrbPosition({
    x: dragOrigin.x + (event.clientX - dragStartPointer.x),
    y: dragOrigin.y + (event.clientY - dragStartPointer.y),
  });
}

function finishOrbDrag(event: PointerEvent): void {
  const target = event.currentTarget;
  if (target instanceof HTMLElement && dragPointerId !== null) {
    try {
      if (target.hasPointerCapture?.(dragPointerId)) {
        target.releasePointerCapture(dragPointerId);
      }
    } catch {
      // ignore
    }
  }
  if (dragPointerId === null) {
    return;
  }
  dragPointerId = null;
  dragOrigin = null;
  dragStartPointer = null;
  orbDragging.value = false;
  orbUserPositioned = true;
  persistOrbPosition();
}

function resetOrbPosition(): void {
  orbUserPositioned = false;
  orbAutoAvoidActive = false;
  const next = defaultOrbPosition();
  if (!next) {
    return;
  }
  orbPosition.value = next;
  persistOrbPosition();
}

let unsubscribeSpeaking: (() => void) | null = null;
let unsubscribeVoiceChunk: (() => void) | null = null;

onMounted(() => {
  unsubscribeSpeaking = subscribeKairoVoiceSpeaking((active) => {
    kairoSpeaking.value = active;
  });
  unsubscribeVoiceChunk = subscribeKairoVoiceChunk(() => {
    voiceBeat.value = true;
    if (voiceBeatTimer !== null) {
      window.clearTimeout(voiceBeatTimer);
    }
    voiceBeatTimer = window.setTimeout(() => {
      voiceBeat.value = false;
      voiceBeatTimer = null;
    }, 220);
  });
  window.requestAnimationFrame(() => {
    syncOrbPosition(true);
    attachBottomHudObserver();
    resolveOrbOverlap();
  });
  window.addEventListener('resize', handleWindowResize);
});

watch([kairoConversationReply, kairoConversationPhase], () => {
  resolveOrbOverlap();
});

onBeforeUnmount(() => {
  clearHoldTimer();
  bottomHudObserver?.disconnect();
  bottomHudObserver = null;
  unsubscribeSpeaking?.();
  unsubscribeVoiceChunk?.();
  if (voiceBeatTimer !== null) {
    window.clearTimeout(voiceBeatTimer);
    voiceBeatTimer = null;
  }
  window.removeEventListener('resize', handleWindowResize);
});
</script>

<template>
  <div
    ref="orbAnchor"
    class="brain-galaxy-stage__jarvis-float"
    :class="{ 'brain-galaxy-stage__jarvis-float--dragging': orbDragging }"
    :style="orbAnchorStyle"
  >
    <button
      type="button"
      class="kairo-galaxy-orb__drag-handle"
      :title="`Drag to move ${personaName} · double-click to reset`"
      :aria-label="`Move ${personaName} orb`"
      @dblclick.stop="resetOrbPosition"
      @pointerdown.stop.prevent="handleOrbDragStart"
      @pointermove.stop.prevent="handleOrbDragMove"
      @pointerup.stop.prevent="finishOrbDrag"
      @pointercancel.stop.prevent="finishOrbDrag"
    >
      Move
    </button>

    <div
      class="kairo-galaxy-orb"
      :class="[
        orbStateClass,
        orbModeClass,
        {
          'kairo-galaxy-orb--ptt': speechCapture.capturing.value,
          'kairo-galaxy-orb--voice-live': kairoSpeaking || shell.kairoSpeechActive,
          'kairo-galaxy-orb--voice-beat': voiceBeat,
          'kairo-galaxy-orb--busy': orbBusy,
        },
      ]"
      :aria-label="`${personaName} voice orb`"
    >
      <button
        type="button"
        class="kairo-galaxy-orb__trigger"
        :disabled="voiceBlocked || !speechCapture.supported"
        :aria-label="
          voiceBlocked
            ? `${personaName} voice muted`
            : handsFreeEnabled
              ? `${personaName} hands-free — tap to switch to manual mode`
              : `${personaName} manual — tap for hands-free, hold to talk`
        "
        @click.stop="handleOrbClick"
        @pointerdown.prevent="handleOrbPointerDown"
        @pointerup.prevent="handleOrbPointerUp"
        @pointercancel.prevent="handleOrbPointerUp"
      >
        <svg
          class="kairo-galaxy-orb__svg"
          viewBox="0 0 200 200"
          role="img"
          aria-hidden="true"
        >
        <defs>
          <radialGradient id="kairo-orb-core-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(72, 196, 255, 0.38)" />
            <stop offset="100%" stop-color="rgba(72, 196, 255, 0)" />
          </radialGradient>
          <radialGradient id="kairo-orb-handsfree-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(92, 255, 180, 0.42)" />
            <stop offset="100%" stop-color="rgba(92, 255, 180, 0)" />
          </radialGradient>
          <linearGradient id="kairo-orb-persona-grad" x1="4" y1="4" x2="20" y2="20" gradientUnits="userSpaceOnUse">
            <stop stop-color="#9ef0ff" />
            <stop offset="0.45" stop-color="#48c4ff" />
            <stop offset="1" stop-color="#e8fbff" />
          </linearGradient>
          <filter id="kairo-orb-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle
          class="kairo-galaxy-orb__halo"
          cx="100"
          cy="100"
          r="92"
          fill="url(#kairo-orb-core-glow)"
        />

        <g class="kairo-galaxy-orb__ticks">
          <line
            v-for="(tick, index) in ticks"
            :key="index"
            :x1="tick.x1"
            :y1="tick.y1"
            :x2="tick.x2"
            :y2="tick.y2"
            :class="{ 'kairo-galaxy-orb__tick--major': tick.major }"
          />
        </g>

        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--outer" cx="100" cy="100" r="72" />
        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--dashed" cx="100" cy="100" r="66" />
        <path
          class="kairo-galaxy-orb__arc"
          d="M 44 100 A 66 66 0 0 1 62 56"
          pathLength="100"
        />

        <g class="kairo-galaxy-orb__beads">
          <circle
            v-for="(bead, index) in beads"
            :key="index"
            class="kairo-galaxy-orb__bead"
            :cx="bead.cx"
            :cy="bead.cy"
            r="2.6"
          />
        </g>

        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--inner" cx="100" cy="100" r="54" />
        <circle class="kairo-galaxy-orb__ring kairo-galaxy-orb__ring--core" cx="100" cy="100" r="46" />

        <text
          class="kairo-galaxy-orb__core-text"
          x="100"
          y="103"
          filter="url(#kairo-orb-glow)"
        >{{ personaOrbLabel }}</text>

        <circle class="kairo-galaxy-orb__beacon" cx="34" cy="34" r="4.5" filter="url(#kairo-orb-glow)" />
        <circle class="kairo-galaxy-orb__sweep" cx="100" cy="100" r="48" />
        <circle class="kairo-galaxy-orb__pulse" cx="100" cy="100" r="56" />
        </svg>
      </button>

      <div class="kairo-galaxy-orb__status">
        <span class="kairo-galaxy-orb__status-dot" aria-hidden="true" />
        <span class="kairo-galaxy-orb__status-label">{{ orbStatusLabel }}</span>
      </div>

      <p v-if="modeLabel" class="kairo-galaxy-orb__mode-pill">{{ modeLabel }}</p>
      <button
        v-if="showInterrupt"
        type="button"
        class="kairo-galaxy-orb__interrupt"
        :title="`Stop ${personaName} (Esc)`"
        :aria-label="`Interrupt ${personaName}`"
        @click.stop="handleInterrupt"
      >
        Interrupt
      </button>
      <p class="kairo-galaxy-orb__hint">{{ hint }}</p>

      <button
        type="button"
        class="kairo-galaxy-orb__model"
        @pointerdown.stop
        @click="shell.focusKairoBriefing()"
      >
        <span aria-hidden="true">◆</span>
        {{ modelLabel }}
      </button>
    </div>
  </div>
</template>
