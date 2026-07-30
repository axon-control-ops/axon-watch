<script setup lang="ts">
import { computed } from 'vue';

import {
  composerAttachmentExtensionLabel,
  composerAttachmentPreviewTitle,
  isComposerImageMime,
  type ComposerClipboardImage,
} from '../../lib/composer-clipboard-paste';

const props = defineProps<{
  attachments: readonly ComposerClipboardImage[];
  disabled?: boolean;
  /** When true, only render the compact attach control (chips live above the form). */
  buttonOnly?: boolean;
  /** When true, only render pending attachment chips. */
  chipsOnly?: boolean;
}>();

const emit = defineEmits<{
  attach: [];
  remove: [id: string];
}>();

const countLabel = computed(() => {
  const n = props.attachments.length;
  return n > 0 ? String(n) : '';
});

const showButton = computed(() => !props.chipsOnly);
const showChips = computed(() => !props.buttonOnly && props.attachments.length > 0);
</script>

<template>
  <div
    class="vaxon-attach"
    :class="{
      'vaxon-attach--button': buttonOnly || (!chipsOnly && !attachments.length),
      'vaxon-attach--chips': chipsOnly || (!buttonOnly && attachments.length > 0),
    }"
  >
    <button
      v-if="showButton"
      type="button"
      class="vaxon-attach__btn"
      :class="{ 'vaxon-attach__btn--active': attachments.length > 0 }"
      :disabled="disabled"
      :title="attachments.length ? `${attachments.length} attached — add more` : 'Attach image or file'"
      :aria-label="attachments.length ? `Attach files, ${attachments.length} pending` : 'Attach image or file'"
      @click="emit('attach')"
    >
      <span class="vaxon-attach__icon" aria-hidden="true">+</span>
      <span v-if="countLabel" class="vaxon-attach__count">{{ countLabel }}</span>
    </button>
    <ul v-if="showChips" class="vaxon-attach__chips" aria-label="Pending attachments">
      <li v-for="item in attachments" :key="item.id" class="vaxon-attach__chip">
        <button
          type="button"
          class="vaxon-attach__preview"
          :title="composerAttachmentPreviewTitle(item.name, item.mimeType)"
          @click.prevent
        >
          <img
            v-if="isComposerImageMime(item.mimeType)"
            :src="item.previewUrl"
            :alt="item.name"
            class="vaxon-attach__thumb"
          />
          <span v-else class="vaxon-attach__ext">
            {{ composerAttachmentExtensionLabel(item.name, item.mimeType) }}
          </span>
        </button>
        <span class="vaxon-attach__name">{{ item.name }}</span>
        <button
          type="button"
          class="vaxon-attach__remove"
          :disabled="disabled"
          :aria-label="`Remove ${item.name}`"
          @click="emit('remove', item.id)"
        >
          ×
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.vaxon-attach {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  flex: 0 0 auto;
  min-width: 0;
}
.vaxon-attach--chips {
  width: 100%;
  flex: 1 1 100%;
}
.vaxon-attach__btn {
  appearance: none;
  border: 1px solid color-mix(in srgb, currentColor 28%, transparent);
  background: transparent;
  color: inherit;
  border-radius: 999px;
  padding: 0.22rem 0.55rem;
  font: inherit;
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  flex-shrink: 0;
  min-width: 1.85rem;
  min-height: 1.85rem;
  line-height: 1;
}
.vaxon-attach__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.vaxon-attach__btn--active {
  border-color: color-mix(in srgb, #5eead4 55%, transparent);
}
.vaxon-attach__icon {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1;
}
.vaxon-attach__count {
  min-width: 1.1rem;
  padding: 0 0.25rem;
  border-radius: 999px;
  background: color-mix(in srgb, #5eead4 28%, transparent);
  font-size: 0.62rem;
  text-align: center;
}
.vaxon-attach__chips {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  width: 100%;
}
.vaxon-attach__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border: 1px solid color-mix(in srgb, currentColor 22%, transparent);
  border-radius: 0.35rem;
  padding: 0.15rem 0.3rem 0.15rem 0.15rem;
  max-width: 11rem;
}
.vaxon-attach__preview {
  appearance: none;
  border: 0;
  background: transparent;
  padding: 0;
  cursor: default;
}
.vaxon-attach__thumb {
  width: 1.5rem;
  height: 1.5rem;
  object-fit: cover;
  border-radius: 0.2rem;
  display: block;
}
.vaxon-attach__ext {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  font-size: 0.55rem;
  font-weight: 700;
  border-radius: 0.2rem;
  background: color-mix(in srgb, currentColor 12%, transparent);
}
.vaxon-attach__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.7rem;
  max-width: 6.5rem;
}
.vaxon-attach__remove {
  appearance: none;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 0.95rem;
  line-height: 1;
  padding: 0 0.15rem;
  opacity: 0.75;
}
</style>
