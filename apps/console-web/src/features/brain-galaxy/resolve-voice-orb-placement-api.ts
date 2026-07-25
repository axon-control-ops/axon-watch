import type { Ref } from 'vue';

import type { VoiceOrbPlacementApi } from './use-kairo-galaxy-orb-drag';

type VoiceOrbShellRefs = {
  voiceOrbPosition: VoiceOrbPlacementApi['voiceOrbPosition'];
  voiceOrbUserPinned: VoiceOrbPlacementApi['voiceOrbUserPinned'];
  voiceOrbDragging: VoiceOrbPlacementApi['voiceOrbDragging'];
  voiceOrbAnchorStyle: VoiceOrbPlacementApi['voiceOrbAnchorStyle'];
};

type VoiceOrbShellActions = {
  setVoiceOrbDock: VoiceOrbPlacementApi['setVoiceOrbDock'];
  setVoiceOrbPosition: VoiceOrbPlacementApi['setVoiceOrbPosition'];
  resetVoiceOrbDock: VoiceOrbPlacementApi['resetVoiceOrbDock'];
  requestVoiceOrbSmartDodge: VoiceOrbPlacementApi['requestVoiceOrbSmartDodge'];
  ensureVoiceOrbPosition: VoiceOrbPlacementApi['ensureVoiceOrbPosition'];
  persistVoiceOrbPlacement: VoiceOrbPlacementApi['persistVoiceOrbPlacement'];
};

export function resolveVoiceOrbPlacementApi(
  mode: 'viewport' | 'embedded',
  refs: VoiceOrbShellRefs,
  actions: VoiceOrbShellActions,
): VoiceOrbPlacementApi | undefined {
  if (mode !== 'viewport') {
    return undefined;
  }
  return {
    voiceOrbPosition: refs.voiceOrbPosition,
    voiceOrbUserPinned: refs.voiceOrbUserPinned,
    voiceOrbDragging: refs.voiceOrbDragging,
    voiceOrbAnchorStyle: refs.voiceOrbAnchorStyle as Ref<Record<string, string> | undefined>,
    setVoiceOrbDock: actions.setVoiceOrbDock,
    setVoiceOrbPosition: actions.setVoiceOrbPosition,
    resetVoiceOrbDock: actions.resetVoiceOrbDock,
    requestVoiceOrbSmartDodge: actions.requestVoiceOrbSmartDodge,
    ensureVoiceOrbPosition: actions.ensureVoiceOrbPosition,
    persistVoiceOrbPlacement: actions.persistVoiceOrbPlacement,
  };
}
