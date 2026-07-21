<script setup lang="ts">
defineProps<{
  saving: boolean;
  dirty: boolean;
}>();

const emit = defineEmits<{
  save: [];
  discard: [];
  reset: [];
}>();
</script>

<template>
  <section class="operator-settings-form__section">
    <header class="operator-settings-form__section-header">
      <h2>Mobile &amp; layout</h2>
      <p>Compact operator surfaces over tunnel or small viewports.</p>
    </header>
    <slot name="mobile" />
  </section>

  <div class="operator-settings-form__actions operator-settings-form__actions--footer">
    <button
      type="button"
      class="operator-settings-form__button"
      :disabled="saving || !dirty"
      @click="emit('save')"
    >
      {{ saving ? 'Saving…' : 'Save' }}
    </button>
    <button
      type="button"
      class="operator-settings-form__button operator-settings-form__button--ghost"
      :disabled="saving || !dirty"
      @click="emit('discard')"
    >
      Discard
    </button>
    <button
      type="button"
      class="operator-settings-form__button operator-settings-form__button--ghost"
      :disabled="saving"
      @click="emit('reset')"
    >
      Reset to defaults
    </button>
  </div>
</template>
