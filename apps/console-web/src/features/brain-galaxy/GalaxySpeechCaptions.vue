<script setup lang="ts">
import { useGalaxySpeechCaptions } from './use-galaxy-speech-captions';

const { captions, speakerAvatar, layoutMode } = useGalaxySpeechCaptions();
</script>

<template>
  <div
    class="galaxy-speech-captions"
    :class="`galaxy-speech-captions--${layoutMode}`"
    aria-live="polite"
    aria-atomic="false"
    :data-active="captions.length > 0 || speakerAvatar ? 'true' : 'false'"
    :data-layout="layoutMode"
  >
    <div
      v-if="speakerAvatar"
      class="galaxy-speech-captions__speaker"
      :data-kind="speakerAvatar.kind"
      :data-speaking="speakerAvatar.speaking ? 'true' : 'false'"
      :aria-label="`${speakerAvatar.name} speaking`"
    >
      <span class="galaxy-speech-captions__avatar-wrap">
        <img
          class="galaxy-speech-captions__face"
          :src="speakerAvatar.faceUrl"
          :alt="speakerAvatar.name"
          width="40"
          height="40"
        >
        <span
          class="galaxy-speech-captions__avatar-fallback"
          :style="{
            background: speakerAvatar.background,
            color: speakerAvatar.foreground,
          }"
          aria-hidden="true"
        >
          {{ speakerAvatar.initials }}
        </span>
      </span>
      <span class="galaxy-speech-captions__speaker-meta">
        <span class="galaxy-speech-captions__speaker-name">{{ speakerAvatar.name }}</span>
        <span class="galaxy-speech-captions__speaker-role">
          {{ speakerAvatar.roleLabel }}
          <template v-if="speakerAvatar.workspaceLabel">
            · {{ speakerAvatar.workspaceLabel }}
          </template>
        </span>
        <span
          v-if="speakerAvatar.activityLine"
          class="galaxy-speech-captions__activity"
        >
          {{ speakerAvatar.activityLine }}
        </span>
      </span>
    </div>
    <p
      v-for="caption in captions"
      :key="caption.id"
      class="galaxy-speech-captions__line"
    >
      {{ caption.text }}
    </p>
  </div>
</template>
