<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const clockLabel = ref('00:00:00 UTC');

function updateClock(): void {
  const now = new Date();
  clockLabel.value = `${now.toISOString().slice(11, 19)} UTC`;
}

let timer: number | undefined;

const watchZone = computed(() => shell.statusBarZones.left.find((item) => item.id === 'watch'));
const agentZone = computed(() => shell.statusBarZones.left.find((item) => item.id === 'agent'));
const versionZone = computed(() => shell.statusBarZones.left.find((item) => item.id === 'version'));
const centerZones = computed(() => shell.statusBarZones.center);
const operatorZone = computed(() => shell.statusBarZones.right[0]);

onMounted(() => {
  updateClock();
  timer = window.setInterval(updateClock, 1000);
});

onUnmounted(() => {
  if (timer) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <footer class="region region-status-bar status-bar-mockup" aria-label="Persistent runtime status">
    <div class="status-bar-mockup__frame">
      <div
        class="status-bar-mockup__chip status-bar-mockup__chip--watch"
        :class="{
          'status-bar-mockup__chip--success': watchZone?.tone === 'success',
          'status-bar-mockup__chip--warning': watchZone?.tone === 'warning',
        }"
      >
        <span
          v-if="watchZone?.tone === 'success'"
          class="status-bar-mockup__dot"
          aria-hidden="true"
        />
        <span class="status-bar-mockup__chip-primary">{{ watchZone?.label }}</span>
        <span class="status-bar-mockup__chip-secondary">
          <span>{{ agentZone?.label }}</span>
          <span class="status-bar-mockup__sep" aria-hidden="true">|</span>
          <span>{{ versionZone?.label }}</span>
        </span>
      </div>

      <span class="status-bar-mockup__rail" aria-hidden="true" />

      <div
        v-for="item in centerZones"
        :key="item.id"
        class="status-bar-mockup__chip"
        :class="{
          'status-bar-mockup__chip--brand': item.tone === 'brand',
          'status-bar-mockup__chip--warning': item.tone === 'warning',
        }"
      >
        <span
          v-if="item.id === 'phase'"
          class="status-bar-mockup__icon status-bar-mockup__icon--phase"
          aria-hidden="true"
        />
        <span
          v-else-if="item.id === 'signals'"
          class="status-bar-mockup__icon status-bar-mockup__icon--signals"
          aria-hidden="true"
        />
        <span class="status-bar-mockup__chip-label">{{ item.label }}</span>
      </div>

      <span class="status-bar-mockup__rail" aria-hidden="true" />

      <div class="status-bar-mockup__chip status-bar-mockup__chip--operator">
        <span class="status-bar-mockup__icon status-bar-mockup__icon--operator" aria-hidden="true" />
        <span class="status-bar-mockup__chip-label">{{ operatorZone?.label }}</span>
      </div>

      <button
        v-if="shell.showKairoBriefingAttention"
        type="button"
        class="status-bar-mockup__chip status-bar-mockup__chip--kairo-briefing"
        :class="`status-bar-mockup__chip--kairo-${shell.kairoBriefingAttention.severity}`"
        :aria-label="`${shell.kairoBriefingAttentionLabel}. Open KAIRO briefing.`"
        @click="shell.setDockHeroMode('briefing')"
      >
        <span class="status-bar-mockup__kairo-pulse" aria-hidden="true" />
        <span class="status-bar-mockup__icon status-bar-mockup__icon--kairo" aria-hidden="true" />
        <span class="status-bar-mockup__chip-label">{{ shell.kairoBriefingAttentionLabel }}</span>
      </button>

      <div class="status-bar-mockup__tail">
        <span class="status-bar-mockup__clock">{{ clockLabel }}</span>
        <span class="status-bar-mockup__sep" aria-hidden="true">|</span>
        <span class="status-bar-mockup__shield" aria-hidden="true">
          ⛨<span class="status-bar-mockup__shield-mark">✓</span>
        </span>
      </div>
    </div>
  </footer>
</template>
