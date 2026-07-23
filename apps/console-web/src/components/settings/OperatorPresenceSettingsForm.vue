<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';
import {
  defaultOperatorPresenceSettings,
  normalizeOperatorPresenceSettings,
} from '../../lib/operator-presence-settings';
import OperatorPresenceHandsFreeFields from './OperatorPresenceHandsFreeFields.vue';
import OperatorPresenceVoiceRoutingFields from './OperatorPresenceVoiceRoutingFields.vue';
import OperatorPresenceSettingsFooter from './OperatorPresenceSettingsFooter.vue';
import OperatorPresenceVoiceTuningFields from './OperatorPresenceVoiceTuningFields.vue';
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

function applyDuplexPreset(settings: OperatorPresenceSettings): void {
  draft.value = settings;
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

const privacyMode = computed({
  get: () => draft.value.privacy_mode,
  set: (value: boolean) => patchDraft({ privacy_mode: value }),
});

const mobileCompactPreferred = computed({
  get: () => draft.value.mobile_compact_preferred,
  set: (value: boolean) => patchDraft({ mobile_compact_preferred: value }),
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

function onNarrationChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (value === 'off' || value === 'minimal' || value === 'conversational') {
    patchDraft({ kairo_narration: value });
  }
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
            <span class="operator-settings-form__pill">{{ draft.speech_rate }}</span>
          </dd>
        </div>
        <div>
          <dt>Speech pitch</dt>
          <dd>
            <span class="operator-settings-form__pill">{{ draft.speech_pitch }}</span>
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
        <OperatorPresenceVoiceTuningFields
          :draft="draft"
          :saving="Boolean(saving)"
          :privacy-mode="privacyMode"
          @patch="patchDraft"
          @test-result="voiceTestResult = $event"
        />
        <p
          v-if="voiceTestResult"
          class="operator-settings-form__voice-result"
          role="status"
          aria-live="polite"
        >
          {{ voiceTestResult }}
        </p>
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
        <OperatorPresenceHandsFreeFields
          :draft="draft"
          :saving="Boolean(saving)"
          :privacy-mode="privacyMode"
          @patch="patchDraft"
          @apply-duplex="applyDuplexPreset"
        />
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
