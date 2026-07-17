<script setup lang="ts">
import type { ComposerMode } from '../../../composables/useAgentDockComposer';
import type { ComposerClipboardImage } from '../../../lib/composer-clipboard-paste';
import type { ComposerAccessTone } from '../../../lib/sandbox-session-view';

type AttachmentChip = {
  key: string;
  label: string;
  kind: string;
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
}>();
</script>

<template>
  <div
    v-if="attachmentChips.length"
    class="agent-dock-composer__chips"
    aria-label="Composer context"
  >
    <button
      v-for="chip in attachmentChips"
      :key="chip.key"
      type="button"
      class="agent-dock-composer__chip"
      :title="chip.label"
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
    aria-label="Attached images"
  >
    <button
      v-for="image in composerImages"
      :key="image.id"
      type="button"
      class="agent-dock-composer__image-card"
      :title="`Open ${image.name}`"
      @click="emit('open-image', image)"
    >
      <img
        class="agent-dock-composer__image-preview"
        :src="image.previewUrl"
        :alt="image.name"
      >
      <button
        type="button"
        class="agent-dock-composer__image-remove"
        :aria-label="`Remove ${image.name}`"
        @click.stop="emit('remove-image', image.id)"
      >
        ×
      </button>
    </button>
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
    <textarea
      id="agent-dock-composer-input"
      :ref="(element) => { props.setInputRef?.(element as HTMLTextAreaElement | null) }"
      :value="draft"
      class="agent-dock-composer__input"
      rows="1"
      :aria-label="composerMode === 'kairo' ? `${operatorPersonaName} composer` : 'Agent composer'"
      :placeholder="placeholder"
      :disabled="!workspaceSelected"
      @input="emit('update:draft', ($event.target as HTMLTextAreaElement).value); emit('sync-height')"
      @keydown="emit('keydown', $event)"
      @paste="emit('paste', $event)"
    />
  </div>

  <div class="agent-dock-composer__footer">
    <div
      v-if="activityChips.length"
      class="agent-dock-composer__activity-chips"
      aria-label="Live agent activity"
    >
      <button
        v-for="chip in activityChips"
        :key="chip.id"
        type="button"
        class="agent-dock-composer__activity-chip"
        :class="`agent-dock-composer__activity-chip--${chip.kind}`"
        :disabled="chip.kind !== 'terminal'"
        @click="chip.kind === 'terminal' ? emit('reveal-terminal') : undefined"
      >
        {{ chip.label }}
      </button>
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
