<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { applyJarvisDuplexPreset } from '../../lib/operator-presence-settings';

const props = defineProps<{
  draft: OperatorPresenceSettings;
  saving?: boolean;
  privacyMode: boolean;
}>();

const emit = defineEmits<{
  patch: [patch: Partial<OperatorPresenceSettings>];
  'apply-duplex': [settings: OperatorPresenceSettings];
}>();

const handsFreeEnabled = computed({
  get: () => props.draft.hands_free_enabled,
  set: (value: boolean) => emit('patch', { hands_free_enabled: value }),
});

const wakeWordConsent = computed({
  get: () => props.draft.wake_word_listening_consent,
  set: (value: boolean) =>
    emit('patch', {
      wake_word_listening_consent: value,
      wake_word_listening_enabled: value ? props.draft.wake_word_listening_enabled : false,
    }),
});

const wakeWordEnabled = computed({
  get: () => props.draft.wake_word_listening_enabled,
  set: (value: boolean) =>
    emit('patch', {
      wake_word_listening_enabled: value,
      wake_word_listening_consent: value ? true : props.draft.wake_word_listening_consent,
    }),
});

const proactiveDuplexEnabled = computed({
  get: () => props.draft.proactive_duplex_enabled,
  set: (value: boolean) => {
    emit('apply-duplex', applyJarvisDuplexPreset(props.draft, value));
  },
});

const spokenAlertsEnabled = computed({
  get: () => props.draft.spoken_alerts_enabled,
  set: (value: boolean) => emit('patch', { spoken_alerts_enabled: value }),
});

const ideVoiceStripEnabled = computed({
  get: () => props.draft.ide_voice_strip_enabled,
  set: (value: boolean) => emit('patch', { ide_voice_strip_enabled: value }),
});

const privacyMode = computed({
  get: () => props.draft.privacy_mode,
  set: (value: boolean) => emit('patch', { privacy_mode: value }),
});
</script>

<template>
  <label class="operator-settings-form__row">
    <input v-model="proactiveDuplexEnabled" type="checkbox" :disabled="saving || privacyMode" />
    <span class="operator-settings-form__copy">
      <strong>JARVIS duplex (proactive speak → listen)</strong>
      <small>
        After VAXON speaks an alert, stay listening for ~30s so you can answer without the wake word.
        Turns on hands-free + spoken alerts. Cold ambient still needs “VAXON”.
      </small>
    </span>
  </label>
  <label class="operator-settings-form__row">
    <input v-model="handsFreeEnabled" type="checkbox" :disabled="saving || privacyMode" />
    <span class="operator-settings-form__copy">
      <strong>Hands-free voice (galaxy orb)</strong>
      <small>
        Listens continuously but only responds when you say "VAXON" or a direct command (e.g. git
        status). Ignores side conversation. Say "stop" to interrupt speech.
      </small>
    </span>
  </label>
  <label class="operator-settings-form__row">
    <input v-model="wakeWordConsent" type="checkbox" :disabled="saving || privacyMode" />
    <span class="operator-settings-form__copy">
      <strong>Local wake-word consent</strong>
      <small>
        Explicit consent for on-device always-listening. Pre-wake audio stays in a local ring buffer
        and is never uploaded. Cloud STT starts only after wake or follow-up.
      </small>
    </span>
  </label>
  <label class="operator-settings-form__row">
    <input
      v-model="wakeWordEnabled"
      type="checkbox"
      :disabled="saving || privacyMode || !draft.wake_word_listening_consent"
    />
    <span class="operator-settings-form__copy">
      <strong>Arm local wake-word engine</strong>
      <small>
        Interim energy gate until open-source WASM keyword evidence passes. Privacy mode is the
        hardware kill switch.
      </small>
    </span>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>Wake sensitivity</strong>
      <small>Lower reduces false wakes; higher catches quieter “VAXON”.</small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.wake_word_sensitivity"
      :disabled="saving || privacyMode || !draft.wake_word_listening_enabled"
      @change="
        emit('patch', {
          wake_word_sensitivity: ($event.target as HTMLSelectElement).value as
            | 'low'
            | 'medium'
            | 'high',
        })
      "
    >
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>Quiet hours (proactive alerts)</strong>
      <small>Local clock HH:MM. Empty disables. Approvals/critical can still escalate once.</small>
    </span>
    <div class="operator-settings-form__slider-grid">
      <input
        type="time"
        :value="draft.quiet_hours_start"
        :disabled="saving"
        @change="
          emit('patch', { quiet_hours_start: ($event.target as HTMLInputElement).value || '' })
        "
      />
      <input
        type="time"
        :value="draft.quiet_hours_end"
        :disabled="saving"
        @change="emit('patch', { quiet_hours_end: ($event.target as HTMLInputElement).value || '' })"
      />
    </div>
  </label>
  <label class="operator-settings-form__row">
    <input v-model="spokenAlertsEnabled" type="checkbox" :disabled="saving || privacyMode" />
    <span class="operator-settings-form__copy">
      <strong>Spoken high-value alerts</strong>
      <small>Interrupt with approvals, degraded runtime, or critical signals.</small>
    </span>
  </label>
  <label class="operator-settings-form__row">
    <input v-model="ideVoiceStripEnabled" type="checkbox" :disabled="saving || privacyMode" />
    <span class="operator-settings-form__copy">
      <strong>IDE voice strip (opt-in)</strong>
      <small>Show the compact voice strip above the IDE editor.</small>
    </span>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--danger">
    <input v-model="privacyMode" type="checkbox" :disabled="saving" />
    <span class="operator-settings-form__copy">
      <strong>Privacy mode</strong>
      <small>Master mute — disables mic capture, TTS, and spoken alerts.</small>
    </span>
  </label>
</template>
