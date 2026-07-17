<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import { useShellStore } from '../../stores/shell';
import { isConnectorStatusBarChip } from '../../lib/connector-glance-view';
import SupportedCommandsFooter from './SupportedCommandsFooter.vue';
import PersonaTitle from '../PersonaTitle.vue';

const shell = useShellStore();
const clockLabel = ref('00:00:00 UTC');

function updateClock(): void {
  const now = new Date();
  clockLabel.value = `${now.toISOString().slice(11, 19)} UTC`;
}

function onCenterChipClick(id: string): void {
  if (!isConnectorStatusBarChip(id)) {
    return;
  }

  void shell.loadConnectors();
  shell.focusWatchConnectors();
}

function connectorChipTitle(id: string): string | undefined {
  if (!isConnectorStatusBarChip(id)) {
    return undefined;
  }

  if (id === 'connector-required-alert') {
    return shell.layoutMode === 'ide'
      ? 'Required connector down — switch to Mission Control connectors'
      : 'Required connector down — open Mission Control connectors';
  }

  return shell.layoutMode === 'ide'
    ? 'Legacy connector offline — switch to Mission Control connectors'
    : 'Open Mission Control connectors';
}

function connectorChipAriaLabel(id: string, label: string): string | undefined {
  if (!isConnectorStatusBarChip(id)) {
    return undefined;
  }

  return `${label}. ${connectorChipTitle(id)}.`;
}

let timer: number | undefined;

const watchZone = computed(() => shell.statusBarZones.left.find((item) => item.id === 'watch'));
const workspaceZone = computed(() => shell.statusBarZones.left.find((item) => item.id === 'workspace'));
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
  <footer
    class="region region-status-bar status-bar-mockup"
    :class="{ 'status-bar-mockup--kairo-cta': shell.showKairoBriefingAttention }"
    aria-label="Persistent runtime status"
  >
    <div class="status-bar-mockup__grid">
      <div class="status-bar-mockup__frame">
        <div
          v-if="watchZone"
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
          <span v-if="agentZone" class="status-bar-mockup__chip-secondary">
            <span>{{ agentZone.label }}</span>
            <span class="status-bar-mockup__sep" aria-hidden="true">|</span>
            <span>{{ versionZone?.label }}</span>
          </span>
        </div>
        <div
          v-else-if="workspaceZone"
          class="status-bar-mockup__chip"
        >
          <span class="status-bar-mockup__chip-primary">{{ workspaceZone.label }}</span>
          <span v-if="versionZone" class="status-bar-mockup__chip-secondary">
            <span>{{ versionZone.label }}</span>
          </span>
        </div>
        <div
          v-else-if="versionZone"
          class="status-bar-mockup__chip"
        >
          <span class="status-bar-mockup__chip-primary">{{ versionZone.label }}</span>
        </div>

        <span class="status-bar-mockup__rail" aria-hidden="true" />

        <component
          :is="isConnectorStatusBarChip(item.id) ? 'button' : 'div'"
          v-for="item in centerZones"
          :key="item.id"
          class="status-bar-mockup__chip"
          :class="{
            'status-bar-mockup__chip--brand': item.tone === 'brand',
            'status-bar-mockup__chip--warning': item.tone === 'warning',
            'status-bar-mockup__chip--connector-glance': item.id === 'connector-glance',
            'status-bar-mockup__chip--connector-required-alert':
              item.id === 'connector-required-alert',
          }"
          :type="isConnectorStatusBarChip(item.id) ? 'button' : undefined"
          :title="connectorChipTitle(item.id)"
          :aria-label="connectorChipAriaLabel(item.id, item.label)"
          @click="isConnectorStatusBarChip(item.id) ? onCenterChipClick(item.id) : undefined"
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
          <span
            v-else-if="item.id === 'connector-glance'"
            class="status-bar-mockup__icon status-bar-mockup__icon--connector-glance"
            aria-hidden="true"
          />
          <span
            v-else-if="item.id === 'connector-required-alert'"
            class="status-bar-mockup__icon status-bar-mockup__icon--connector-required-alert"
            aria-hidden="true"
          />
          <span class="status-bar-mockup__chip-label">{{ item.label }}</span>
        </component>

        <span class="status-bar-mockup__rail" aria-hidden="true" />

        <div class="status-bar-mockup__chip status-bar-mockup__chip--operator">
          <span class="status-bar-mockup__icon status-bar-mockup__icon--operator" aria-hidden="true" />
          <span class="status-bar-mockup__chip-label">{{ operatorZone?.label }}</span>
        </div>

        <div
          id="status-bar-galaxy-actions"
          class="status-bar-mockup__galaxy-actions"
          aria-label="Galaxy view controls"
        />

        <SupportedCommandsFooter v-if="shell.layoutMode === 'operator'" />

        <div class="status-bar-mockup__tail">
          <span class="status-bar-mockup__clock">{{ clockLabel }}</span>
          <span class="status-bar-mockup__sep" aria-hidden="true">|</span>
          <span class="status-bar-mockup__shield" aria-hidden="true">
            ⛨<span class="status-bar-mockup__shield-mark">✓</span>
          </span>
        </div>
      </div>

      <div class="status-bar-mockup__hero-rail">
        <button
          v-if="shell.showKairoBriefingAttention"
          type="button"
          class="status-bar-mockup__kairo-cta"
          :class="`status-bar-mockup__kairo-cta--${shell.kairoBriefingAttention.severity}`"
          :aria-label="`${shell.kairoBriefingAttentionLabel}. Open operator briefing.`"
          @click="shell.focusKairoBriefing()"
        >
          <span class="status-bar-mockup__kairo-cta-glow" aria-hidden="true" />
          <span class="status-bar-mockup__kairo-cta-label">
            Open <PersonaTitle suffix="Briefing" mark-size="xs" />
          </span>
          <span class="status-bar-mockup__kairo-cta-badge" aria-hidden="true">
            {{ shell.kairoBriefingAttention.badgeCount }}
          </span>
        </button>
      </div>
    </div>
  </footer>
</template>
