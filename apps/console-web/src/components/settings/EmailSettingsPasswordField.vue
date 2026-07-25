<script setup lang="ts">
import { ref } from 'vue';

defineProps<{
  modelValue: string;
  label: string;
  placeholder?: string;
  showToggle?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const visible = ref(false);
</script>

<template>
  <label>
    <span>{{ label }}</span>
    <div class="email-settings-panel__password-field">
      <input
        :value="modelValue"
        :type="visible ? 'text' : 'password'"
        autocomplete="new-password"
        :placeholder="placeholder"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <button
        v-if="showToggle !== false"
        type="button"
        class="email-settings-panel__password-toggle"
        :aria-pressed="visible"
        :aria-label="visible ? `Hide ${label}` : `Show ${label}`"
        @click="visible = !visible"
      >
        {{ visible ? 'Hide' : 'Show' }}
      </button>
    </div>
  </label>
</template>
