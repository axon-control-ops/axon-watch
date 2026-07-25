<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';
import { kairoVoiceLastReason } from '../../lib/kairo-voice-diagnostics';
import {
  applyJarvisDuplexPreset,
  defaultOperatorPresenceSettings,
  formatVoiceTuningValue,
  normalizeOperatorPresenceSettings,
} from '../../lib/operator-presence-settings';
import OperatorPresenceVoiceRoutingFields from './OperatorPresenceVoiceRoutingFields.vue';
import OperatorPresenceSettingsFooter from './OperatorPresenceSettingsFooter.vue';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  settings: OperatorPresenceSettings;
  saving?: boolean;
  persist: (settings: OperatorPresenceSettings) => Promise<void>;
}>();

const emit = defineEmits<{
  dirty: [dirty: boolean];
}>();

const shell = useShellStore();

const draft = ref<OperatorPresenceSettings>(normalizeOperatorPresenceSettings(props.settings));
const dirty = ref(false);
const voiceTesting = ref(false);
const voiceTestResult = ref<string | null>(null);

watch(
  () => props.settings,
  (next) => {
    if (dirty.value) {
      return;
    }
    draft.value = normalizeOperatorPresenceSettings(next);
  },
  { deep: true },
);

watch(dirty, (value) => {
  emit('dirty', value);
});

function markDirty(): void {
  dirty.value = true;
}

function patchDraft(patch: Partial<OperatorPresenceSettings>): void {
  draft.value = normalizeOperatorPresenceSettings({
    ...draft.value,
    ...patch,
  });
  markDirty();
}

const configuredNarration = computed(() => draft.value.kairo_narration ?? 'minimal');
const effectiveNarration = computed(() => shell.effectiveKairoNarrationLevel);
const narrationOverridden = computed(
  () => configuredNarration.value !== effectiveNarration.value,
);

const personaEnabled = computed({
  get: () => draft.value.operator_persona_enabled,
  set: (value: boolean) => patchDraft({ operator_persona_enabled: value }),
});

const spokenAlertsEnabled = computed({
  get: () => draft.value.spoken_alerts_enabled,
  set: (value: boolean) => patchDraft({ spoken_alerts_enabled: value }),
});

const ideVoiceStripEnabled = computed({
  get: () => draft.value.ide_voice_strip_enabled,
  set: (value: boolean) => patchDraft({ ide_voice_strip_enabled: value }),
});

const privacyMode = computed({
  get: () => draft.value.privacy_mode,
  set: (value: boolean) => patchDraft({ privacy_mode: value }),
});

const mobileCompactPreferred = computed({
  get: () => draft.value.mobile_compact_preferred,
  set: (value: boolean) => patchDraft({ mobile_compact_preferred: value }),
});

const handsFreeEnabled = computed({
  get: () => draft.value.hands_free_enabled,
  set: (value: boolean) => patchDraft({ hands_free_enabled: value }),
});

const proactiveDuplexEnabled = computed({
  get: () => draft.value.proactive_duplex_enabled,
  set: (value: boolean) => {
    draft.value = applyJarvisDuplexPreset(draft.value, value);
    markDirty();
  },
});

const narrateToolProgress = computed({
  get: () => draft.value.narrate_tool_progress,
  set: (value: boolean) => patchDraft({ narrate_tool_progress: value }),
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
    hint: 'Start, done, alerts, and up to three thinking lines while the agent works (browser voice).',
  },
  {
    value: 'conversational',
    label: 'Conversational',
    hint: 'Same as Minimal with polished phrasing; optional tool milestones when enabled below.',
  },
] as const;

const speechRateDisplay = computed(() => formatVoiceTuningValue(draft.value.speech_rate ?? 1));
const speechPitchDisplay = computed(() =>
  formatVoiceTuningValue(draft.value.speech_pitch ?? 1.04),
);

function onNarrationChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (value === 'off' || value === 'minimal' || value === 'conversational') {
    patchDraft({ kairo_narration: value });
  }
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

async function commitSave(): Promise<void> {
  if (props.saving || !dirty.value) {
    return;
  }
  try {
    await props.persist(normalizeOperatorPresenceSettings(draft.value));
    dirty.value = false;
  } catch {
    // Keep dirty so the operator can retry; store surface shows the error.
  }
}

async function flushIfDirty(): Promise<boolean> {
  if (!dirty.value || props.saving) {
    return false;
  }
  try {
    await props.persist(normalizeOperatorPresenceSettings(draft.value));
    dirty.value = false;
    return true;
  } catch {
    return false;
  }
}

function discardDraft(): void {
  draft.value = normalizeOperatorPresenceSettings(props.settings);
  dirty.value = false;
}

function requestReset(): void {
  if (props.saving) {
    return;
  }
  draft.value = defaultOperatorPresenceSettings();
  markDirty();
}

async function testVoiceSample(): Promise<void> {
  if (draft.value.privacy_mode || draft.value.kairo_narration === 'off') {
    voiceTestResult.value = 'Enable narration and disable privacy mode to test voice.';
    return;
  }
  voiceTesting.value = true;
  voiceTestResult.value = null;
  try {
    const engine = await shell.testKairoVoiceFromSettings({
      speechRate: draft.value.speech_rate,
      speechPitch: draft.value.speech_pitch,
    });
    if (engine === 'azure') {
      voiceTestResult.value = 'Azure neural voice played successfully.';
    } else if (engine === 'browser') {
      const reason = kairoVoiceLastReason.value;
      if (reason === 'vault_locked') {
        voiceTestResult.value =
          'Browser fallback — unlock Vault (AZURE_SPEECH_KEY) for neural TTS.';
      } else if (reason === 'missing_key') {
        voiceTestResult.value =
          'Browser fallback — add AZURE_SPEECH_KEY to Vault for neural TTS.';
      } else {
        voiceTestResult.value = `Browser fallback voice played (${reason || 'Azure unavailable'}).`;
      }
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

defineExpose({
  dirty,
  flushIfDirty,
  discardDraft,
});
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
          <dd>{{ draft.privacy_mode ? 'Muted' : 'Voice allowed' }}</dd>
        </div>
        <div>
          <dt>Spoken alerts</dt>
          <dd>{{ draft.spoken_alerts_enabled ? 'On' : 'Off' }}</dd>
        </div>
        <div>
          <dt>Speech rate</dt>
          <dd>
            <span class="operator-settings-form__pill">{{ speechRateDisplay }}</span>
          </dd>
        </div>
        <div>
          <dt>Speech pitch</dt>
          <dd>
            <span class="operator-settings-form__pill">{{ speechPitchDisplay }}</span>
          </dd>
        </div>
      </dl>
      <p v-if="dirty" class="operator-settings-form__status-note">
        Unsaved changes — Save, or leave Settings to auto-save.
      </p>
      <p v-else-if="narrationOverridden" class="operator-settings-form__status-note">
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
            <small>Agent runs speak bookends and throttled thinking — not every tool by default.</small>
          </span>
          <select
            class="operator-settings-form__select"
            :value="draft.kairo_narration"
            :disabled="saving"
            @change="onNarrationChange"
          >
            <option v-for="option in narrationOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <p class="operator-settings-form__option-hint">
            {{
              narrationOptions.find((option) => option.value === draft.kairo_narration)?.hint ??
              ''
            }}
          </p>
        </label>
        <label class="operator-settings-form__row">
          <input
            v-model="narrateToolProgress"
            type="checkbox"
            :disabled="saving || privacyMode || draft.kairo_narration !== 'conversational'"
          />
          <span class="operator-settings-form__copy">
            <strong>Tool milestone narration</strong>
            <small>
              Conversational only — speak tool steps at most once every 30 seconds when enabled.
            </small>
          </span>
        </label>
        <div class="operator-settings-form__voice-tuning">
          <header class="operator-settings-form__copy">
            <strong>Voice tuning</strong>
            <small>
              Same controls as Axon Signal — continuous rate/pitch for Azure neural and browser
              fallback. Drag freely, then Save (or leave Settings to auto-save).
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
          </div>
        </div>
        <div class="operator-settings-form__actions">
          <button
            type="button"
            class="operator-settings-form__button"
            :disabled="saving || voiceTesting || draft.privacy_mode || draft.kairo_narration === 'off'"
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
        <OperatorPresenceVoiceRoutingFields
          :draft="draft"
          :saving="Boolean(saving)"
          :privacy-mode="privacyMode"
          @patch="patchDraft"
        />
        <label class="operator-settings-form__row">
          <input
            v-model="proactiveDuplexEnabled"
            type="checkbox"
            :disabled="saving || privacyMode"
          />
          <span class="operator-settings-form__copy">
            <strong>JARVIS duplex (proactive speak → listen)</strong>
            <small>
              After VAXON speaks an alert, stay listening for ~30s so you can answer without the wake
              word. Turns on hands-free + spoken alerts. Cold ambient still needs “VAXON”.
            </small>
          </span>
        </label>
        <label class="operator-settings-form__row">
          <input v-model="handsFreeEnabled" type="checkbox" :disabled="saving || privacyMode" />
          <span class="operator-settings-form__copy">
            <strong>Hands-free voice (galaxy orb)</strong>
            <small>
              Listens continuously but only responds when you say "VAXON" or a direct command
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

      <OperatorPresenceSettingsFooter
        :saving="Boolean(saving)"
        :dirty="dirty"
        @save="commitSave"
        @discard="discardDraft"
        @reset="requestReset"
      >
        <template #mobile>
          <label class="operator-settings-form__row">
            <input v-model="mobileCompactPreferred" type="checkbox" :disabled="saving" />
            <span class="operator-settings-form__copy">
              <strong>Prefer compact mobile layout</strong>
              <small>Use the field-unit cockpit when the viewport is narrow.</small>
            </span>
          </label>
        </template>
      </OperatorPresenceSettingsFooter>
    </div>
  </div>
</template>
