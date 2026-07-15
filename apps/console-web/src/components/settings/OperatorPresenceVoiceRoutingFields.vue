<script setup lang="ts">
import type { OperatorPresenceSettings } from '../../contracts/canonical';

const props = defineProps<{
  draft: OperatorPresenceSettings;
  saving: boolean;
  privacyMode: boolean;
}>();

const emit = defineEmits<{
  patch: [patch: Partial<OperatorPresenceSettings>];
}>();

function onAzureVoiceChange(event: Event): void {
  emit('patch', { azure_voice_id: (event.target as HTMLSelectElement).value });
}

function onSttModeChange(event: Event): void {
  emit('patch', {
    stt_mode: (event.target as HTMLSelectElement).value as OperatorPresenceSettings['stt_mode'],
  });
}

function onVoiceRoutingChange(event: Event): void {
  emit('patch', {
    voice_routing_mode: (event.target as HTMLSelectElement)
      .value as OperatorPresenceSettings['voice_routing_mode'],
  });
}
</script>

<template>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>Azure voice</strong>
      <small>Neural TTS voice for VAXON (browser TTS remains the fallback).</small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.azure_voice_id"
      :disabled="saving || privacyMode || draft.kairo_narration === 'off'"
      @change="onAzureVoiceChange"
    >
      <option value="en-GB-RyanNeural">en-GB-RyanNeural</option>
      <option value="en-US-GuyNeural">en-US-GuyNeural</option>
      <option value="en-US-JennyNeural">en-US-JennyNeural</option>
      <option value="en-GB-SoniaNeural">en-GB-SoniaNeural</option>
    </select>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>Speech-to-text mode</strong>
      <small>Browser Web Speech is default; cloud is optional with browser fallback.</small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.stt_mode"
      :disabled="saving || privacyMode"
      @change="onSttModeChange"
    >
      <option value="browser">Browser</option>
      <option value="browser_continuous">Browser continuous</option>
      <option value="cloud">Cloud (optional)</option>
    </select>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>VAXON voice routing</strong>
      <small>Independent from IDE Composer. Template-first keeps voice local.</small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.voice_routing_mode"
      :disabled="saving"
      @change="onVoiceRoutingChange"
    >
      <option value="template_first">Template first</option>
      <option value="runtime_on_deep">Runtime on deep</option>
      <option value="runtime_aggressive">Runtime aggressive</option>
    </select>
  </label>
</template>
