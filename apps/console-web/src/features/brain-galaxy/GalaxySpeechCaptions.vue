<script setup lang="ts">
import { useGalaxySpeechCaptions } from './use-galaxy-speech-captions';

const { captions } = useGalaxySpeechCaptions();
</script>

<template>
  <div
    class="galaxy-speech-captions"
    aria-live="polite"
    aria-atomic="false"
    :data-active="captions.length > 0 ? 'true' : 'false'"
  >
    <p
      v-for="caption in captions"
      :key="caption.id"
      class="galaxy-speech-captions__line"
    >
      {{ caption.text }}
    </p>
  </div>
</template>
