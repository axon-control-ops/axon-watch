<script setup lang="ts">
import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { VAXON_MODEL_OPTIONS } from '../../lib/operator-presence-settings';

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

function onVaxonModelChange(event: Event): void {
  emit('patch', {
    vaxon_model_id: (event.target as HTMLSelectElement).value,
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
      <small>Azure cloud STT is default (Whisper-class accuracy); browser Web Speech is fallback.</small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.stt_mode"
      :disabled="saving || privacyMode"
      @change="onSttModeChange"
    >
      <option value="cloud">Azure cloud (recommended)</option>
      <option value="browser">Browser</option>
      <option value="browser_continuous">Browser continuous</option>
    </select>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>VAXON voice routing</strong>
      <small>
        Independent from IDE Composer. Prefer Runtime on deep for conversational
        answers; Template first is the low-credit local fallback.
      </small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.voice_routing_mode"
      :disabled="saving"
      @change="onVoiceRoutingChange"
    >
      <option value="runtime_on_deep">Runtime on deep (recommended)</option>
      <option value="runtime_aggressive">Runtime aggressive</option>
      <option value="template_first">Template first (low credit)</option>
    </select>
  </label>
  <label class="operator-settings-form__row operator-settings-form__row--select">
    <span class="operator-settings-form__copy">
      <strong>VAXON model</strong>
      <small>
        Operator-global LLM for VAXON conversation and narration — never tied to a
        workspace Agent Dock model.
      </small>
    </span>
    <select
      class="operator-settings-form__select"
      :value="draft.vaxon_model_id"
      :disabled="saving"
      @change="onVaxonModelChange"
    >
      <option
        v-for="option in VAXON_MODEL_OPTIONS"
        :key="option.id"
        :value="option.id"
      >
        {{ option.label }}{{ option.id === 'cursor-grok-4.5-high-fast' ? ' (recommended)' : '' }}
      </option>
    </select>
  </label>
</template>
