<script setup lang="ts">
import { SANDBOX_SESSION_CONSENT_LINES } from '../../../lib/sandbox-session-view';

defineProps<{
  show: boolean;
  checked: boolean;
  pending?: boolean;
  error?: string;
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
      aria-labelledby="sandbox-session-consent-title"
      @click.self="emit('cancel')"
    >
      <div class="agent-dock-full-access-consent__card">
        <p id="sandbox-session-consent-title" class="agent-dock-full-access-consent__title">
          Enable Sandbox session?
        </p>
        <ul class="agent-dock-full-access-consent__list">
          <li v-for="line in SANDBOX_SESSION_CONSENT_LINES" :key="line">{{ line }}</li>
        </ul>
        <label class="agent-dock-full-access-consent__check">
          <input
            :checked="checked"
            type="checkbox"
            :disabled="pending"
            @change="emit('update:checked', ($event.target as HTMLInputElement).checked)"
          >
          <span>I understand Sandbox work stays in a disposable copy for this session.</span>
        </label>
        <p
          v-if="error"
          class="agent-dock-full-access-consent__error"
          role="alert"
        >
          {{ error }}
        </p>
        <div class="agent-dock-full-access-consent__actions">
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--cancel"
            :disabled="pending"
            @click="emit('cancel')"
          >
            Cancel
          </button>
          <button
            type="button"
            class="agent-dock-full-access-consent__btn agent-dock-full-access-consent__btn--confirm"
            :disabled="!checked || pending"
            @click="emit('confirm')"
          >
            {{ pending ? 'Enabling…' : 'Enable Sandbox' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
