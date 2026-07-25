import { computed, ref, type Ref } from 'vue';

import type { OrbBoxSize, OrbPosition } from '../../../features/brain-galaxy/kairo-galaxy-orb-position';
import {
  clampPlacementToViewport,
  collectObstacleRects,
  DEFAULT_VOICE_ORB_DOCK,
  normalizeVoiceOrbDock,
  readVoiceOrbPlacementFromStorage,
  resolvePlacementForDock,
  resolveSmartDodgePlacement,
  type VoiceOrbDock,
  type VoiceOrbPlacementState,
  VOICE_ORB_VIEWPORT_MARGINS,
  writeVoiceOrbPlacementToStorage,
} from '../../../features/brain-galaxy/voice-orb-placement';

function defaultOrbSize(): OrbBoxSize {
  return { width: 212, height: 268 };
}

function readViewportSize(): OrbBoxSize {
  if (typeof window === 'undefined') {
    return { width: 1280, height: 800 };
  }
  return { width: window.innerWidth, height: window.innerHeight };
}

function measureOrbSize(orbAnchor: HTMLElement | null): OrbBoxSize {
  if (!orbAnchor) {
    return defaultOrbSize();
  }
  const width = orbAnchor.offsetWidth || defaultOrbSize().width;
  const height = orbAnchor.offsetHeight || defaultOrbSize().height;
  return { width, height };
}

export function createVoiceOrbPlacementController() {
  const restored = readVoiceOrbPlacementFromStorage();
  const voiceOrbDock = ref<VoiceOrbDock | 'custom'>(restored?.dock ?? DEFAULT_VOICE_ORB_DOCK);
  const voiceOrbPosition = ref<OrbPosition | null>(
    restored ? { x: restored.x, y: restored.y } : null,
  );
  const voiceOrbUserPinned = ref(restored?.userPinned === true);
  const voiceOrbDragging = ref(false);
  const voiceOrbVisible = ref(restored?.visible !== false);

  function persist(): void {
    if (!voiceOrbPosition.value) {
      writeVoiceOrbPlacementToStorage({
        dock: voiceOrbDock.value,
        x: 0,
        y: 0,
        userPinned: voiceOrbUserPinned.value,
        visible: voiceOrbVisible.value,
      });
      return;
    }
    const state: VoiceOrbPlacementState = {
      dock: voiceOrbDock.value,
      x: voiceOrbPosition.value.x,
      y: voiceOrbPosition.value.y,
      userPinned: voiceOrbUserPinned.value,
      visible: voiceOrbVisible.value,
    };
    writeVoiceOrbPlacementToStorage(state);
  }

  function applyPosition(
    position: OrbPosition,
    dock: VoiceOrbDock | 'custom',
    options?: { persist?: boolean; pin?: boolean },
  ): void {
    const viewport = readViewportSize();
    const clamped = clampPlacementToViewport({
      position,
      viewport,
      orb: defaultOrbSize(),
      margins: VOICE_ORB_VIEWPORT_MARGINS,
    });
    voiceOrbPosition.value = clamped;
    voiceOrbDock.value = dock;
    if (options?.pin === true) {
      voiceOrbUserPinned.value = true;
    }
    if (options?.pin === false) {
      voiceOrbUserPinned.value = false;
    }
    if (options?.persist !== false) {
      persist();
    }
  }

  function setVoiceOrbDock(dockInput: string | VoiceOrbDock): void {
    const dock = normalizeVoiceOrbDock(dockInput) ?? DEFAULT_VOICE_ORB_DOCK;
    const viewport = readViewportSize();
    const position = resolvePlacementForDock({
      dock,
      viewport,
      orb: defaultOrbSize(),
    });
    applyPosition(position, dock, { pin: false });
  }

  function setVoiceOrbPosition(
    position: OrbPosition,
    options?: { pin?: boolean; persist?: boolean },
  ): void {
    applyPosition(position, 'custom', {
      pin: options?.pin ?? true,
      persist: options?.persist,
    });
  }

  function resetVoiceOrbDock(): void {
    voiceOrbUserPinned.value = false;
    setVoiceOrbDock(DEFAULT_VOICE_ORB_DOCK);
  }

  function setVoiceOrbVisible(visible: boolean): void {
    voiceOrbVisible.value = visible;
    persist();
  }

  function hideVoiceOrb(): void {
    setVoiceOrbVisible(false);
  }

  function showVoiceOrb(): void {
    setVoiceOrbVisible(true);
  }

  function requestVoiceOrbSmartDodge(options?: { force?: boolean; preferredDock?: VoiceOrbDock }): void {
    if (voiceOrbDragging.value) {
      return;
    }
    if (voiceOrbUserPinned.value && options?.force !== true) {
      return;
    }
    const viewport = readViewportSize();
    const obstacles = collectObstacleRects(typeof document !== 'undefined' ? document : null);
    const result = resolveSmartDodgePlacement({
      viewport,
      orb: defaultOrbSize(),
      obstacles,
      preferredDock: options?.preferredDock ?? DEFAULT_VOICE_ORB_DOCK,
    });
    applyPosition(result.position, result.dock, { pin: false });
  }

  function ensureVoiceOrbPosition(orbAnchor: HTMLElement | null): OrbPosition {
    const viewport = readViewportSize();
    const orb = measureOrbSize(orbAnchor);
    if (voiceOrbPosition.value) {
      const clamped = clampPlacementToViewport({
        position: voiceOrbPosition.value,
        viewport,
        orb,
      });
      voiceOrbPosition.value = clamped;
      return clamped;
    }
    const dock =
      voiceOrbDock.value === 'custom' ? DEFAULT_VOICE_ORB_DOCK : voiceOrbDock.value;
    const position = resolvePlacementForDock({ dock, viewport, orb });
    voiceOrbPosition.value = position;
    voiceOrbDock.value = dock;
    persist();
    return position;
  }

  const voiceOrbAnchorStyle = computed<Record<string, string> | undefined>(() => {
    if (!voiceOrbPosition.value) {
      return undefined;
    }
    return {
      left: `${voiceOrbPosition.value.x}px`,
      top: `${voiceOrbPosition.value.y}px`,
    };
  });

  return {
    voiceOrbDock: voiceOrbDock as Ref<VoiceOrbDock | 'custom'>,
    voiceOrbPosition,
    voiceOrbUserPinned,
    voiceOrbDragging,
    voiceOrbVisible,
    voiceOrbAnchorStyle,
    setVoiceOrbDock,
    setVoiceOrbPosition,
    resetVoiceOrbDock,
    setVoiceOrbVisible,
    hideVoiceOrb,
    showVoiceOrb,
    requestVoiceOrbSmartDodge,
    ensureVoiceOrbPosition,
    persistVoiceOrbPlacement: persist,
  };
}

export type VoiceOrbPlacementController = ReturnType<typeof createVoiceOrbPlacementController>;
