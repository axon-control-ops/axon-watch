<script setup lang="ts">
import { FULL_ACCESS_CONSENT_LINES } from '../../../lib/agent-dock-activity-view';

defineProps<{
  show: boolean;
  checked: boolean;
}>();

const emit = defineEmits<{
  'update:checked': [value: boolean];
  cancel: [];
  confirm: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="agent-dock-full-access-consent"
      role="dialog"
      aria-modal="true"
      aria-labelledby="full-access-consent-title"
      @click.self="emit('cancel')"
    >
      <div class="agent-dock-full-access-consent__card">
        <p id="full-access-consent-title" class="agent-dock-full-access-consent__title">
          Enable Full Access?
        </p>
        <ul class="agent-dock-full-access-consent__list">
          <li v-for="line in FULL_ACCESS_CONSENT_LINES" :key="line">{{ line }}</li>
        </ul>
        <label class="agent-dock-full-access-consent__check">
          <input
            :checked="checked"
            type="checkbox"
            @change="emit('update:checked', ($event.target as HTMLInputElement).checked)"
          >
          <span>I understand and consent to Full Access for Agent and Debug turns in this workspace.</span>
        </label>
        <div class="agent-dock-full-access-consent__actions">
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--cancel"
            @click="emit('cancel')"
          >
            Cancel
          </button>
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--confirm"
            :disabled="!checked"
            @click="emit('confirm')"
          >
            Enable Full Access
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
