<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

const emit = defineEmits<{
  complete: [];
}>();

const BOOT_LINES = [
  'control-plane · linking',
  'axon-watch · linking',
  'runtime summary · ready',
  'KAIRO · standing by',
] as const;

const visibleLines = ref(0);
const canSkip = ref(false);
let timers: number[] = [];

function finish(): void {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers = [];
  emit('complete');
}

function skip(): void {
  finish();
}

onMounted(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reducedMotion) {
    finish();
    return;
  }

  timers.push(
    window.setTimeout(() => {
      canSkip.value = true;
    }, 500),
  );

  BOOT_LINES.forEach((_, index) => {
    timers.push(
      window.setTimeout(() => {
        visibleLines.value = index + 1;
        if (index === BOOT_LINES.length - 1) {
          timers.push(window.setTimeout(finish, 420));
        }
      }, 380 * (index + 1)),
    );
  });
});

onUnmounted(() => {
  timers.forEach((timer) => window.clearTimeout(timer));
  timers = [];
});
</script>

<template>
  <div class="boot-wake" role="dialog" aria-label="AXON-X system wake">
    <div class="boot-wake__panel">
      <p class="boot-wake__brand">AXON-X</p>
      <p class="boot-wake__subtitle">Knowledge-Augmented Intelligence for Response and Oversight</p>

      <ul class="boot-wake__lines">
        <li
          v-for="(line, index) in BOOT_LINES"
          :key="line"
          class="boot-wake__line"
          :class="{ 'boot-wake__line--visible': index < visibleLines }"
        >
          {{ line }}
        </li>
      </ul>

      <button
        v-if="canSkip"
        type="button"
        class="boot-wake__skip"
        @click="skip"
      >
        Enter console
      </button>
    </div>
  </div>
</template>
