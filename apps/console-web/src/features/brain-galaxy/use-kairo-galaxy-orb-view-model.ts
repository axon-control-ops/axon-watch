import { computed, type ComputedRef, type Ref } from 'vue';

import {
  galaxyOrbHint,
  galaxyOrbModeClass,
  galaxyOrbModeLabel,
  galaxyOrbModelLabel,
  galaxyOrbStateClass,
  galaxyOrbStatusLabel,
  galaxyOrbTriggerAriaLabel,
} from './kairo-galaxy-orb-view';
import type { KairoPresenceState } from '../../lib/kairo-presence';
import { kairoCaptureMode } from '../kairo-conversation/kairo-shared-speech-capture';
import { kairoConversationPhase } from '../kairo-conversation/kairo-conversation-state';
import { mapLegacyPhaseToDuplex } from '../kairo-conversation/kairo-duplex-phase';
import { isKairoVoiceFollowupWindowActive } from '../../lib/kairo-voice-followup-window';

type SpeechCaptureLike = {
  capturing: Ref<boolean>;
};

/** Shared orb HUD labels / classes so KairoGalaxyOrb.vue stays under the ratchet. */
export function useKairoGalaxyOrbViewModel(input: {
  personaName: string;
  presenceState: ComputedRef<KairoPresenceState> | Ref<KairoPresenceState>;
  speaking: ComputedRef<boolean>;
  speechCapture: SpeechCaptureLike;
  agentStreamActive: ComputedRef<boolean> | Ref<boolean> | boolean;
  handsFreeEnabled: ComputedRef<boolean> | Ref<boolean>;
  handsFreeArmed: ComputedRef<boolean> | Ref<boolean>;
  gateFeedback: ComputedRef<string | null> | Ref<string | null>;
  voiceBlocked: ComputedRef<boolean> | Ref<boolean>;
  selectedComposerModel: ComputedRef<string | null> | Ref<string | null> | string | null;
}): {
  captureMode: ComputedRef<string>;
  orbStateClass: ComputedRef<string>;
  orbModeClass: ComputedRef<string>;
  modelLabel: ComputedRef<string>;
  hint: ComputedRef<string>;
  modeLabel: ComputedRef<string>;
  orbStatusLabel: ComputedRef<string>;
  triggerAriaLabel: ComputedRef<string>;
} {
  const captureMode = computed(() => kairoCaptureMode.value);
  const unwrap = <T>(value: ComputedRef<T> | Ref<T> | T): T =>
    value && typeof value === 'object' && 'value' in (value as object)
      ? ((value as Ref<T>).value as T)
      : (value as T);

  const orbStateClass = computed(() => {
    const presence = unwrap(input.presenceState);
    const duplexPhase = mapLegacyPhaseToDuplex(kairoConversationPhase.value, {
      followupActive: isKairoVoiceFollowupWindowActive(),
      privacyMuted: presence === 'privacy_blocked',
      alerting: presence === 'alerting',
    });
    return galaxyOrbStateClass(
      presence,
      unwrap(input.speaking),
      kairoConversationPhase.value,
      input.speechCapture.capturing.value,
      Boolean(unwrap(input.agentStreamActive)),
      captureMode.value,
      duplexPhase,
    );
  });
  const orbModeClass = computed(() => galaxyOrbModeClass(unwrap(input.handsFreeEnabled)));
  const modelLabel = computed(() =>
    galaxyOrbModelLabel(unwrap(input.selectedComposerModel) ?? null),
  );
  const hint = computed(() =>
    galaxyOrbHint(
      unwrap(input.presenceState),
      unwrap(input.speaking),
      kairoConversationPhase.value,
      unwrap(input.handsFreeArmed),
      unwrap(input.gateFeedback),
    ),
  );
  const modeLabel = computed(() =>
    galaxyOrbModeLabel(
      unwrap(input.handsFreeEnabled),
      kairoConversationPhase.value,
      unwrap(input.handsFreeArmed),
    ),
  );
  const orbStatusLabel = computed(() =>
    galaxyOrbStatusLabel(
      kairoConversationPhase.value,
      unwrap(input.speaking),
      input.speechCapture.capturing.value,
      captureMode.value,
    ),
  );
  const triggerAriaLabel = computed(() =>
    galaxyOrbTriggerAriaLabel(
      input.personaName,
      unwrap(input.voiceBlocked),
      unwrap(input.handsFreeArmed),
    ),
  );

  return {
    captureMode,
    orbStateClass,
    orbModeClass,
    modelLabel,
    hint,
    modeLabel,
    orbStatusLabel,
    triggerAriaLabel,
  };
}
