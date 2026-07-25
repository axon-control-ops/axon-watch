<script setup lang="ts">
import { computed } from 'vue';

import type { ComposerMode } from '../../../composables/useAgentDockComposer';
import type { ComposerTypeaheadRow } from '../../../composables/agent-dock/use-composer-typeahead';
import {
  type ComposerClipboardImage,
  composerAttachmentExtensionLabel,
  composerAttachmentPreviewTitle,
  isComposerImageMime,
} from '../../../lib/composer-clipboard-paste';
import type { ComposerAccessTone } from '../../../lib/sandbox-session-view';
import {
  COMPOSER_TYPEAHEAD_LISTBOX_ID,
  composerTypeaheadActiveDescendant,
} from '../../../lib/composer-typeahead-view';
import AgentDockComposerTypeahead from './AgentDockComposerTypeahead.vue';

type AttachmentChip = {
  key: string;
  label: string;
  kind: string;
  title?: string;
};

type ActivityChip = {
  id: string;
  label: string;
  kind: string;
};

type QueuedMessage = {
  id: string;
  content: string;
};

const props = defineProps<{
  /** Bind parent textarea ref — do not pass a Vue Ref as a prop (templates unwrap it to null). */
  setInputRef: (el: HTMLTextAreaElement | null) => void;
  draft: string;
  composerMode: ComposerMode;
  operatorPersonaName: string;
  placeholder: string;
  workspaceSelected: boolean;
  attachmentChips: AttachmentChip[];
  composerImages: ComposerClipboardImage[];
  queueItems: QueuedMessage[];
  queueSummary: string;
  activityChips: ActivityChip[];
  composerQueueHint: string;
  showComposerResume: boolean;
  composerResumeLabel: string;
  showComposerSteer: boolean;
  showComposerStop: boolean;
  canSubmitComposer: boolean;
  composerSubmitLabel: string;
  accessTone?: ComposerAccessTone | null;
  commandMutationState: string;
  runMutationState: string;
  kairoPending: boolean;
  speechCaptureSupported: boolean;
  speechCapturing: boolean;
  privacyMode: boolean;
  typeaheadOpen?: boolean;
  typeaheadCaption?: string;
  typeaheadLoading?: boolean;
  typeaheadRows?: ComposerTypeaheadRow[];
  typeaheadSelectedIndex?: number;
}>();

const emit = defineEmits<{
  'update:draft': [value: string];
  'remove-chip': [key: string];
  'open-image': [image: ComposerClipboardImage];
  'remove-image': [imageId: string];
  'edit-queued': [messageId: string];
  'remove-queued': [messageId: string];
  'steer-queued': [messageId: string];
  'sync-height': [];
  keydown: [event: KeyboardEvent];
  paste: [event: ClipboardEvent];
  'reveal-terminal': [];
  resume: [];
  steer: [];
  'toggle-voice': [];
  stop: [];
  'typeahead-select': [row: ComposerTypeaheadRow];
  'typeahead-hover': [index: number];
  'sync-typeahead': [];
}>();

const typeaheadActiveDescendantId = computed(() =>
  composerTypeaheadActiveDescendant(
    Boolean(props.typeaheadOpen),
    props.typeaheadRows?.length ?? 0,
    props.typeaheadSelectedIndex ?? 0,
  ),
);

const skillChips = computed(() =>
  props.attachmentChips.filter((chip) => chip.kind === 'skill'),
);

const contextChips = computed(() =>
  props.attachmentChips.filter((chip) => chip.kind !== 'skill'),
);
</script>

<template>
  <div
    v-if="contextChips.length"
    class="agent-dock-composer__chips"
    aria-label="Composer context"
  >
    <button
      v-for="chip in contextChips"
      :key="chip.key"
      type="button"
      class="agent-dock-composer__chip"
      :title="chip.title || chip.label"
      @click="emit('remove-chip', chip.key)"
    >
      <span class="agent-dock-composer__chip-kind">{{ chip.kind }}</span>
      <span class="agent-dock-composer__chip-label">{{ chip.label }}</span>
      <span class="agent-dock-composer__chip-remove" aria-hidden="true">×</span>
    </button>
  </div>

  <div
    v-if="composerImages.length"
    class="agent-dock-composer__image-strip"
    aria-label="Attached files"
  >
    <div
      v-for="image in composerImages"
      :key="image.id"
      class="agent-dock-composer__image-card"
      :class="{ 'agent-dock-composer__image-card--file': !isComposerImageMime(image.mimeType) }"
    >
      <button
        type="button"
        class="agent-dock-composer__image-open"
        :title="composerAttachmentPreviewTitle(image.name, image.mimeType)"
        :aria-label="composerAttachmentPreviewTitle(image.name, image.mimeType)"
        @click="emit('open-image', image)"
      >
        <img
          v-if="isComposerImageMime(image.mimeType)"
          class="agent-dock-composer__image-preview"
          :src="image.previewUrl"
          :alt="image.name"
          loading="lazy"
        >
        <span
          v-else
          class="agent-dock-composer__file-preview"
        >
          <span class="agent-dock-composer__file-ext">
            {{ composerAttachmentExtensionLabel(image.name, image.mimeType) }}
          </span>
          <span class="agent-dock-composer__file-name">{{ image.name }}</span>
        </span>
      </button>
      <button
        type="button"
        class="agent-dock-composer__image-remove"
        :aria-label="`Remove ${image.name}`"
        @click.stop="emit('remove-image', image.id)"
      >
        ×
      </button>
    </div>
  </div>

  <div
    v-if="queueItems.length"
    class="agent-dock-composer__queue"
    role="status"
    aria-live="polite"
  >
    <p class="agent-dock-composer__queue-summary">
      {{ queueSummary }}
    </p>
    <ul class="agent-dock-composer__queue-list">
      <li
        v-for="item in queueItems"
        :key="item.id"
        class="agent-dock-composer__queue-item"
      >
        <span class="agent-dock-composer__queue-text">{{ item.content }}</span>
        <div class="agent-dock-composer__queue-actions">
          <button
            type="button"
            class="agent-dock-composer__queue-edit"
            aria-label="Edit queued message"
            title="Edit"
            @click="emit('edit-queued', item.id)"
          >
            Edit
          </button>
          <button
            type="button"
            class="agent-dock-composer__queue-steer"
            aria-label="Send queued message now"
            title="Send now"
            @click="emit('steer-queued', item.id)"
          >
            ↑
          </button>
          <button
            type="button"
            class="agent-dock-composer__queue-remove"
            aria-label="Remove queued message"
            @click="emit('remove-queued', item.id)"
          >
            ×
          </button>
        </div>
      </li>
    </ul>
  </div>

  <div class="agent-dock-composer__input-row">
    <AgentDockComposerTypeahead
      :open="Boolean(typeaheadOpen)"
      :caption="typeaheadCaption || ''"
      :loading="Boolean(typeaheadLoading)"
      :rows="typeaheadRows || []"
      :selected-index="typeaheadSelectedIndex || 0"
      @select="emit('typeahead-select', $event)"
      @hover="emit('typeahead-hover', $event)"
    />
    <div class="agent-dock-composer__field">
      <div
        v-if="skillChips.length"
        class="agent-dock-composer__inline-chips"
        aria-label="Attached skills"
      >
        <button
          v-for="chip in skillChips"
          :key="chip.key"
          type="button"
          class="agent-dock-composer__chip agent-dock-composer__chip--skill"
          :title="chip.title || chip.label"
          @click="emit('remove-chip', chip.key)"
        >
          <span
            class="agent-dock-composer__chip-icon"
            aria-hidden="true"
          >✦</span>
          <span class="agent-dock-composer__chip-label">{{ chip.label }}</span>
          <span class="agent-dock-composer__chip-remove" aria-hidden="true">×</span>
        </button>
      </div>
      <textarea
        id="agent-dock-composer-input"
        :ref="(element) => { props.setInputRef?.(element as HTMLTextAreaElement | null) }"
        :value="draft"
        class="agent-dock-composer__input"
        rows="1"
        :aria-label="composerMode === 'kairo' ? `${operatorPersonaName} composer` : 'Agent composer'"
        :placeholder="placeholder"
        :disabled="!workspaceSelected"
        autocomplete="off"
        spellcheck="true"
        :aria-expanded="Boolean(typeaheadOpen)"
        :aria-controls="typeaheadOpen ? COMPOSER_TYPEAHEAD_LISTBOX_ID : undefined"
        :aria-activedescendant="typeaheadActiveDescendantId"
        aria-autocomplete="list"
        @input="emit('update:draft', ($event.target as HTMLTextAreaElement).value); emit('sync-height')"
        @keydown="emit('keydown', $event)"
        @keyup="emit('sync-typeahead')"
        @click="emit('sync-typeahead')"
        @paste="emit('paste', $event)"
      />
    </div>
  </div>

  <div class="agent-dock-composer__footer">
    <div
      v-if="activityChips.length"
      class="agent-dock-composer__activity-chips"
      aria-label="Live agent activity"
    >
      <template
        v-for="chip in activityChips"
        :key="chip.id"
      >
        <button
          v-if="chip.kind === 'terminal'"
          type="button"
          class="agent-dock-composer__activity-chip agent-dock-composer__activity-chip--terminal"
          aria-label="Reveal terminal panel"
          @click="emit('reveal-terminal')"
        >
          {{ chip.label }}
        </button>
        <span
          v-else
          class="agent-dock-composer__activity-chip"
          :class="`agent-dock-composer__activity-chip--${chip.kind}`"
        >
          {{ chip.label }}
        </span>
      </template>
    </div>

    <slot name="toolbar" />

    <div class="agent-dock-composer__actions">
      <p
        v-if="composerQueueHint"
        class="agent-dock-composer__queue-hint"
      >
        {{ composerQueueHint }}
      </p>
      <button
        v-if="showComposerResume"
        type="button"
        class="agent-dock-composer__resume"
        :disabled="runMutationState === 'resuming'"
        @click="emit('resume')"
      >
        {{ composerResumeLabel }}
      </button>
      <button
        v-if="composerMode === 'kairo' && speechCaptureSupported"
        type="button"
        class="agent-dock-composer__tool agent-dock-composer__tool--mic"
        :class="{ 'is-active': speechCapturing }"
        :disabled="privacyMode || kairoPending"
        @click="emit('toggle-voice')"
      >
        {{ speechCapturing ? 'Listening…' : 'Mic' }}
      </button>
      <button
        v-if="showComposerSteer"
        type="button"
        class="agent-dock-composer__send agent-dock-composer__send--steer"
        :disabled="runMutationState === 'stopping' || commandMutationState === 'submitting'"
        aria-label="Steer now"
        title="Steer now (interrupt and send)"
        @click="emit('steer')"
      >
        <span class="agent-dock-composer__send-icon" aria-hidden="true">↑</span>
      </button>
      <button
        v-if="showComposerStop"
        type="button"
        class="agent-dock-composer__send agent-dock-composer__send--stop"
        :disabled="runMutationState === 'stopping'"
        :aria-label="runMutationState === 'stopping' ? 'Stopping run' : 'Stop run'"
        @click="emit('stop')"
      >
        <span
          v-if="runMutationState === 'stopping'"
          class="agent-dock-composer__send-spinner"
          aria-hidden="true"
        />
        <span v-else class="agent-dock-composer__stop-icon" aria-hidden="true" />
      </button>
      <button
        v-else
        type="submit"
        class="agent-dock-composer__send"
        :class="{
          [`agent-dock-composer__send--${accessTone}`]: Boolean(accessTone),
        }"
        :disabled="!canSubmitComposer"
        :aria-label="composerSubmitLabel"
        :title="composerSubmitLabel"
      >
        <span
          v-if="commandMutationState === 'submitting' || (composerMode === 'kairo' && kairoPending)"
          class="agent-dock-composer__send-spinner"
          aria-hidden="true"
        />
        <span v-else class="agent-dock-composer__send-icon" aria-hidden="true">
          {{ composerMode === 'kairo' ? 'Ask' : '↑' }}
        </span>
      </button>
    </div>
  </div>
</template>
