<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';

import type { OperatorPresenceSettings } from '../../contracts/canonical';

const props = defineProps<{
  open: boolean;
  settings: OperatorPresenceSettings;
  saving?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  save: [patch: Partial<OperatorPresenceSettings>];
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);

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

const narrationOptions = [
  { value: 'off', label: 'Off' },
  { value: 'minimal', label: 'Minimal (start, done, interrupts)' },
  { value: 'conversational', label: 'Conversational (model-generated)' },
] as const;

function onNarrationChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (value === 'off' || value === 'minimal' || value === 'conversational') {
    emit('save', { kairo_narration: value });
  }
}

function syncDialogOpenState(open: boolean): void {
  const dialog = dialogRef.value;
  if (!dialog) {
    return;
  }
  if (open) {
    if (!dialog.open) {
      dialog.showModal();
    }
    return;
  }
  if (dialog.open) {
    dialog.close();
  }
}

function onDialogClose(): void {
  emit('close');
}

function onDialogClick(event: MouseEvent): void {
  if (event.target === dialogRef.value) {
    emit('close');
  }
}

watch(
  () => props.open,
  (open) => {
    syncDialogOpenState(open);
  },
  { flush: 'post' },
);

watch(dialogRef, (dialog) => {
  if (dialog) {
    syncDialogOpenState(props.open);
  }
});

onUnmounted(() => {
  dialogRef.value?.close();
});
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialogRef"
      class="operator-presence-settings-dialog"
      aria-label="Operator presence settings"
      @close="onDialogClose"
      @click="onDialogClick"
    >
      <div class="operator-presence-settings__panel" @click.stop>
        <div class="operator-presence-settings__header">
          <strong>Operator presence</strong>
          <button type="button" class="operator-presence-settings__close" @click="emit('close')">
            Close
          </button>
        </div>
        <label class="operator-presence-settings__row">
          <input v-model="personaEnabled" type="checkbox" :disabled="saving" />
          <span>KAIRO persona copy</span>
        </label>
        <label class="operator-presence-settings__row">
          <input v-model="spokenAlertsEnabled" type="checkbox" :disabled="saving" />
          <span>Spoken high-value alerts</span>
        </label>
        <label class="operator-presence-settings__row">
          <input v-model="ideVoiceStripEnabled" type="checkbox" :disabled="saving" />
          <span>IDE voice strip (opt-in)</span>
        </label>
        <label class="operator-presence-settings__row operator-presence-settings__row--select">
          <span>KAIRO narration</span>
          <select
            class="operator-presence-settings__select"
            :value="settings.kairo_narration"
            :disabled="saving"
            @change="onNarrationChange"
          >
            <option v-for="option in narrationOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <p class="operator-presence-settings__hint">
          Changes tone and spoken delivery only. Run state, signals, and approvals stay canonical.
          IDE quiet tier mutes narration unless conversational is selected.
        </p>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.operator-presence-settings-dialog {
  position: fixed;
  top: calc(var(--topbar-height, 56px) + 0.5rem);
  right: 0.85rem;
  left: auto;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  max-width: min(18rem, calc(100vw - 1.7rem));
}

.operator-presence-settings-dialog::backdrop {
  background: rgba(4, 8, 14, 0.55);
  backdrop-filter: blur(2px);
}

.operator-presence-settings__panel {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.5rem;
  background: rgba(12, 16, 22, 0.98);
  padding: 0.75rem;
  box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.45);
}

.operator-presence-settings__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.operator-presence-settings__close {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.operator-presence-settings__row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.operator-presence-settings__row--select {
  flex-direction: column;
  align-items: stretch;
  gap: 0.35rem;
  margin-top: 0.5rem;
}

.operator-presence-settings__select {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  font: inherit;
  padding: 0.35rem 0.5rem;
}

.operator-presence-settings__hint {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  opacity: 0.72;
}
</style>
