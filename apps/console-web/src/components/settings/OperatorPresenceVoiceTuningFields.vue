<script setup lang="ts">
import { computed } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { kairoVoiceLastReason } from '../../lib/kairo-voice-diagnostics';
import {
  formatVoiceTuningValue,
} from '../../lib/operator-presence-settings';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  draft: OperatorPresenceSettings;
  saving?: boolean;
  privacyMode: boolean;
}>();

const emit = defineEmits<{
  patch: [patch: Partial<OperatorPresenceSettings>];
  'test-result': [message: string | null];
}>();

const shell = useShellStore();

const speechRateDisplay = computed(() => formatVoiceTuningValue(props.draft.speech_rate ?? 1));
const speechPitchDisplay = computed(() =>
  formatVoiceTuningValue(props.draft.speech_pitch ?? 1.04),
);

function patchDraft(patch: Partial<OperatorPresenceSettings>): void {
  emit('patch', patch);
}

function onSpeechRateInput(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  patchDraft({ speech_rate: Math.round(value * 100) / 100 });
}

function onSpeechPitchInput(event: Event): void {
  const value = Number((event.target as HTMLInputElement).value);
  if (!Number.isFinite(value)) {
    return;
  }
  patchDraft({ speech_pitch: Math.round(value * 100) / 100 });
}

function resetVoiceTuning(): void {
  patchDraft({
    speech_rate: 1.0,
    speech_pitch: 1.04,
    azure_voice_id: 'en-GB-RyanNeural',
  });
}

async function testVoiceSample(): Promise<void> {
  if (props.draft.privacy_mode || props.draft.kairo_narration === 'off') {
    emit('test-result', 'Enable narration and disable privacy mode to test voice.');
    return;
  }
  emit('test-result', null);
  try {
    const engine = await shell.testKairoVoiceFromSettings({
      speechRate: props.draft.speech_rate,
      speechPitch: props.draft.speech_pitch,
    });
    if (engine === 'azure') {
      emit('test-result', 'Azure neural voice played successfully.');
    } else if (engine === 'browser') {
      const reason = kairoVoiceLastReason.value;
      if (reason === 'vault_locked') {
        emit('test-result', 'Browser fallback — unlock Vault (AZURE_SPEECH_KEY) for neural TTS.');
      } else if (reason === 'missing_key') {
        emit('test-result', 'Browser fallback — add AZURE_SPEECH_KEY to Vault for neural TTS.');
      } else {
        emit('test-result', `Browser fallback voice played (${reason || 'Azure unavailable'}).`);
      }
    } else {
      emit('test-result', 'Voice skipped — check privacy mode and narration level.');
    }
  } catch (error) {
    emit(
      'test-result',
      error instanceof Error ? error.message : 'Voice test failed — is the control plane running?',
    );
  }
}
</script>

<template>
  <div class="operator-settings-form__voice-tuning">
    <header class="operator-settings-form__copy">
      <strong>Voice tuning</strong>
      <small>
        Same controls as Axon Signal — continuous rate/pitch for Azure neural and browser fallback.
        Drag freely, then Save (or leave Settings to auto-save).
      </small>
    </header>
    <div class="operator-settings-form__slider-grid">
      <label class="operator-settings-form__slider">
        <span class="operator-settings-form__slider-head">
          <span>Speech rate</span>
          <span class="operator-settings-form__slider-value">{{ speechRateDisplay }}</span>
        </span>
        <input
          type="range"
          min="0.5"
          max="1.3"
          step="0.02"
          :value="draft.speech_rate"
          :disabled="saving || privacyMode || draft.kairo_narration === 'off'"
          @input="onSpeechRateInput"
        />
        <span class="operator-settings-form__slider-ends">
          <span>0.50 slow</span><span>1.00 default</span><span>1.30 fast</span>
        </span>
      </label>
      <label class="operator-settings-form__slider">
        <span class="operator-settings-form__slider-head">
          <span>Speech pitch</span>
          <span class="operator-settings-form__slider-value">{{ speechPitchDisplay }}</span>
        </span>
        <input
          type="range"
          min="0.5"
          max="1.5"
          step="0.02"
          :value="draft.speech_pitch"
          :disabled="saving || privacyMode || draft.kairo_narration === 'off'"
          @input="onSpeechPitchInput"
        />
        <span class="operator-settings-form__slider-ends">
          <span>0.50 deep</span><span>1.04 default</span><span>1.50 high</span>
        </span>
      </label>
    </div>
    <div class="operator-settings-form__actions operator-settings-form__actions--inline">
      <button
        type="button"
        class="operator-settings-form__button operator-settings-form__button--ghost"
        :disabled="saving || privacyMode || draft.kairo_narration === 'off'"
        @click="resetVoiceTuning"
      >
        Reset voice defaults
      </button>
      <button
        type="button"
        class="operator-settings-form__button"
        :disabled="saving || draft.privacy_mode || draft.kairo_narration === 'off'"
        @click="testVoiceSample"
      >
        Test voice sample
      </button>
    </div>
  </div>
</template>
