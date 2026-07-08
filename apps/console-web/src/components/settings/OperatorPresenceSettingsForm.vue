<script setup lang="ts">
import { computed, ref } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  settings: OperatorPresenceSettings;
  saving?: boolean;
}>();

const emit = defineEmits<{
  save: [patch: Partial<OperatorPresenceSettings>];
  reset: [];
}>();

const shell = useShellStore();

const voiceTesting = ref(false);
const voiceTestResult = ref<string | null>(null);

const configuredNarration = computed(() => props.settings.kairo_narration ?? 'minimal');
const effectiveNarration = computed(() => shell.effectiveKairoNarrationLevel);
const narrationOverridden = computed(
  () => configuredNarration.value !== effectiveNarration.value,
);

const personaEnabled = computed({
  get: () => props.settings.operator_persona_enabled,
  set: (value: boolean) => emit('save', { operator_persona_enabled: value }),
});

const spokenAlertsEnabled = computed({
  get: () => props.settings.spoken_alerts_enabled,
  set: (value: boolean) => emit('save', { spoken_alerts_enabled: value }),
});

const ideVoiceStripEnabled = computed({
  get: () => props.settings.ide_voice_strip_enabled,
  set: (value: boolean) => emit('save', { ide_voice_strip_enabled: value }),
});

const privacyMode = computed({
  get: () => props.settings.privacy_mode,
  set: (value: boolean) => emit('save', { privacy_mode: value }),
});

const mobileCompactPreferred = computed({
  get: () => props.settings.mobile_compact_preferred,
  set: (value: boolean) => emit('save', { mobile_compact_preferred: value }),
});

const handsFreeEnabled = computed({
  get: () => props.settings.hands_free_enabled,
  set: (value: boolean) => emit('save', { hands_free_enabled: value }),
});

const narrationOptions = [
  {
    value: 'off',
    label: 'Off',
    hint: 'Text only — no spoken lines from KAIRO.',
  },
  {
    value: 'minimal',
    label: 'Minimal',
    hint: 'Start, done, and high-value interrupts only.',
  },
  {
    value: 'conversational',
    label: 'Conversational',
    hint: 'JARVIS-style paraphrase for dialogue and voice replies.',
  },
] as const;

function onNarrationChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (value === 'off' || value === 'minimal' || value === 'conversational') {
    emit('save', { kairo_narration: value });
  }
}

async function testVoiceSample(): Promise<void> {
  if (props.settings.privacy_mode || props.settings.kairo_narration === 'off') {
    voiceTestResult.value = 'Enable narration and disable privacy mode to test voice.';
    return;
  }
  voiceTesting.value = true;
  voiceTestResult.value = null;
  try {
    const engine = await shell.testKairoVoiceFromSettings();
    if (engine === 'azure') {
      voiceTestResult.value = 'Azure voice played successfully.';
    } else if (engine === 'browser') {
      voiceTestResult.value = 'Browser fallback voice played (Azure unavailable).';
    } else {
      voiceTestResult.value = 'Voice skipped — check privacy mode and narration level.';
    }
  } catch (error) {
    voiceTestResult.value =
      error instanceof Error ? error.message : 'Voice test failed — is the control plane running?';
  } finally {
    voiceTesting.value = false;
  }
}

function requestReset(): void {
  if (props.saving) {
    return;
  }
  emit('reset');
}
</script>

<template>
  <div class="operator-settings-form">
    <aside class="operator-settings-form__status-card" aria-label="Live KAIRO status">
      <h2 class="operator-settings-form__status-title">Live status</h2>
      <dl class="operator-settings-form__status-grid">
        <div>
          <dt>Configured narration</dt>
          <dd>
            <span class="operator-settings-form__pill">{{ configuredNarration }}</span>
          </dd>
        </div>
        <div>
          <dt>Effective narration</dt>
          <dd>
            <span class="operator-settings-form__pill">{{ effectiveNarration }}</span>
          </dd>
        </div>
        <div>
          <dt>Privacy</dt>
          <dd>{{ settings.privacy_mode ? 'Muted' : 'Voice allowed' }}</dd>
        </div>
        <div>
          <dt>Spoken alerts</dt>
          <dd>{{ settings.spoken_alerts_enabled ? 'On' : 'Off' }}</dd>
        </div>
      </dl>
      <p v-if="narrationOverridden" class="operator-settings-form__status-note">
        Effective narration differs in IDE quiet mode unless conversational is selected.
      </p>
    </aside>

    <div class="operator-settings-form__sections">
      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>KAIRO presence</h2>
          <p>Persona and narration — changes tone only; run state stays canonical.</p>
        </header>
        <label class="operator-settings-form__row">
          <input v-model="personaEnabled" type="checkbox" :disabled="saving" />
          <span class="operator-settings-form__copy">
            <strong>KAIRO persona copy</strong>
            <small>Dry, witty JARVIS-forward phrasing in Ask mode and spoken lines.</small>
          </span>
        </label>
        <label class="operator-settings-form__row operator-settings-form__row--select">
          <span class="operator-settings-form__copy">
            <strong>KAIRO narration</strong>
            <small>Choose how much KAIRO speaks during operator work.</small>
          </span>
          <select
            class="operator-settings-form__select"
            :value="settings.kairo_narration"
            :disabled="saving"
            @change="onNarrationChange"
          >
            <option v-for="option in narrationOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <p class="operator-settings-form__option-hint">
            {{
              narrationOptions.find((option) => option.value === settings.kairo_narration)?.hint ??
              ''
            }}
          </p>
        </label>
        <div class="operator-settings-form__actions">
          <button
            type="button"
            class="operator-settings-form__button"
            :disabled="saving || voiceTesting || settings.privacy_mode || settings.kairo_narration === 'off'"
            @click="testVoiceSample"
          >
            {{ voiceTesting ? 'Testing voice…' : 'Test voice sample' }}
          </button>
          <p
            v-if="voiceTestResult"
            class="operator-settings-form__voice-result"
            role="status"
            aria-live="polite"
          >
            {{ voiceTestResult }}
          </p>
        </div>
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Voice &amp; alerts</h2>
          <p>When KAIRO may speak aloud during operator work.</p>
        </header>
      <label class="operator-settings-form__row">
        <input v-model="handsFreeEnabled" type="checkbox" :disabled="saving || privacyMode" />
        <span class="operator-settings-form__copy">
          <strong>Hands-free voice (galaxy orb)</strong>
          <small>
            Listens continuously but only responds when you say "KAIRO" or a direct command
            (e.g. git status). Ignores side conversation. Say "stop" to interrupt speech.
          </small>
        </span>
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
      </section>

      <section class="operator-settings-form__section">
        <header class="operator-settings-form__section-header">
          <h2>Mobile &amp; layout</h2>
          <p>Compact operator surfaces over tunnel or small viewports.</p>
        </header>
        <label class="operator-settings-form__row">
          <input v-model="mobileCompactPreferred" type="checkbox" :disabled="saving" />
          <span class="operator-settings-form__copy">
            <strong>Prefer compact mobile layout</strong>
            <small>Use the field-unit cockpit when the viewport is narrow.</small>
          </span>
        </label>
      </section>

      <div class="operator-settings-form__actions operator-settings-form__actions--footer">
        <button
          type="button"
          class="operator-settings-form__button operator-settings-form__button--ghost"
          :disabled="saving"
          @click="requestReset"
        >
          Reset to defaults
        </button>
      </div>
    </div>
  </div>
</template>
