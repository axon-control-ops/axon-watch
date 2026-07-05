<script setup lang="ts">
import { computed } from 'vue';

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

const personaEnabled = computed({
  get: () => props.settings.operator_persona_enabled,
  set: (value: boolean) => emit('save', { operator_persona_enabled: value }),
});

const spokenAlertsEnabled = computed({
  get: () => props.settings.spoken_alerts_enabled,
  set: (value: boolean) => emit('save', { spoken_alerts_enabled: value }),
});
</script>

<template>
  <div v-if="open" class="operator-presence-settings" role="dialog" aria-label="Operator presence settings">
    <div class="operator-presence-settings__panel">
      <div class="operator-presence-settings__header">
        <strong>Operator presence</strong>
        <button type="button" class="operator-presence-settings__close" @click="emit('close')">
          Close
        </button>
      </div>
      <label class="operator-presence-settings__row">
        <input
          v-model="personaEnabled"
          type="checkbox"
          :disabled="saving"
        />
        <span>KAIRO persona copy</span>
      </label>
      <label class="operator-presence-settings__row">
        <input
          v-model="spokenAlertsEnabled"
          type="checkbox"
          :disabled="saving"
        />
        <span>Spoken high-value alerts</span>
      </label>
      <p class="operator-presence-settings__hint">
        Changes tone and spoken delivery only. Run state, signals, and approvals stay canonical.
      </p>
    </div>
  </div>
</template>

<style scoped>
.operator-presence-settings {
  position: absolute;
  inset: calc(100% + 0.35rem) 0 auto auto;
  z-index: 30;
  min-width: 16rem;
}

.operator-presence-settings__panel {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.5rem;
  background: rgba(12, 16, 22, 0.96);
  padding: 0.75rem;
  box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.35);
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

.operator-presence-settings__hint {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  opacity: 0.72;
}
</style>
