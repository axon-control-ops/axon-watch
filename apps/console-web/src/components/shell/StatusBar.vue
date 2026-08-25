<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import {
  openRuntimeUsageSettings,
  openWatchConnectors,
} from '../../composables/useIdeEditorStatusBar';
import { openOperatorStandup } from '../../features/kairo-conversation/open-operator-standup';
import { openRecoveryCenter } from '../../features/recovery-center/recovery-overlay-state';
import { isClaudeUsageStatusBarChip } from '../../lib/claude-usage-view';
import { isConnectorStatusBarChip } from '../../lib/connector-glance-view';
import { isCursorUsageStatusBarChip } from '../../lib/cursor-usage-view';
import { useSandboxPreviewServers } from '../../composables/use-sandbox-preview-servers';
import { useShellStore } from '../../stores/shell';
import SupportedCommandsFooter from './SupportedCommandsFooter.vue';
import PersonaTitle from '../PersonaTitle.vue';

const shell = useShellStore();
const clockLabel = ref('00:00:00');
const previewServers = useSandboxPreviewServers(() => shell.currentWorkspace?.workspace_id);
const previewChipRef = ref<HTMLElement | null>(null);
// The status bar frame sets `overflow: hidden`, so an absolutely positioned
// panel inside it is clipped away. The panel is teleported to <body> and
// anchored to the chip's measured rect instead.
const previewAnchor = ref({ left: 0, bottom: 0 });

function togglePreviewPanel(): void {
  const rect = previewChipRef.value?.getBoundingClientRect();
  if (rect) {
    previewAnchor.value = {
      left: Math.min(rect.left, window.innerWidth - 340),
      bottom: window.innerHeight - rect.top + 6,
    };
  }
  previewServers.togglePanel();
}

function updateClock(): void {
  const now = new Date();
  clockLabel.value = now.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

async function onOpenStandup(): Promise<void> {
  await openOperatorStandup(shell);
}

function isInteractiveCenterChip(id: string): boolean {
  return (
    isConnectorStatusBarChip(id) ||
    isCursorUsageStatusBarChip(id) ||
    isClaudeUsageStatusBarChip(id) ||
    id === 'attention' ||
    id === 'phase'
  );
}

function onCenterChipClick(id: string): void {
  if (id === 'attention' || id === 'phase') {
    void openRecoveryCenter(shell.currentWorkspace?.workspace_id);
    return;
  }
  if (isCursorUsageStatusBarChip(id) || isClaudeUsageStatusBarChip(id)) {
    openRuntimeUsageSettings(shell);
    return;
  }
  if (!isConnectorStatusBarChip(id)) {
    return;
  }

  openWatchConnectors(shell);
}

function connectorChipTitle(id: string): string | undefined {
  if (isCursorUsageStatusBarChip(id) || isClaudeUsageStatusBarChip(id)) {
    return shell.statusBarZones.center.find((item) => item.id === id)?.title;
  }
  if (!isConnectorStatusBarChip(id)) {
    return undefined;
  }

  if (id === 'connector-required-alert') {
    return shell.layoutMode === 'ide'
      ? 'Required connector down — switch to Mission Control connectors'
      : 'Required connector down — open Mission Control connectors';
  }

  if (id === 'watch-offline') {
    return 'Watch offline — connector probes paused until the watch reconnects';
  }

  return shell.layoutMode === 'ide'
    ? 'Legacy connector offline — switch to Mission Control connectors'
    : 'Open Mission Control connectors';
}

function connectorChipAriaLabel(id: string, label: string): string | undefined {
  if (isCursorUsageStatusBarChip(id) || isClaudeUsageStatusBarChip(id)) {
    return (
      shell.statusBarZones.center.find((item) => item.id === id)?.ariaLabel ??
      `${label}. Open runtime usage settings.`
    );
  }
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
  if (shell.runtimeStatusLoadState === 'idle') {
    void shell.loadRuntimeStatus();
  }
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
          :is="isInteractiveCenterChip(item.id) ? 'button' : 'div'"
          v-for="item in centerZones"
          :key="item.id"
          class="status-bar-mockup__chip"
          :class="{
            'status-bar-mockup__chip--brand': item.tone === 'brand',
            'status-bar-mockup__chip--success':
              item.tone === 'success' && (item.id === 'cursor-usage' || item.id === 'claude-usage'),
            'status-bar-mockup__chip--warning':
              item.tone === 'warning' && item.id !== 'watch-offline',
            'status-bar-mockup__chip--connector-glance': item.id === 'connector-glance',
            'status-bar-mockup__chip--connector-required-alert':
              item.id === 'connector-required-alert',
            'status-bar-mockup__chip--watch-offline': item.id === 'watch-offline',
            'status-bar-mockup__chip--cursor-usage': item.id === 'cursor-usage',
            'status-bar-mockup__chip--claude-usage': item.id === 'claude-usage',
          }"
          :type="isInteractiveCenterChip(item.id) ? 'button' : undefined"
          :title="connectorChipTitle(item.id) ?? item.title"
          :aria-label="connectorChipAriaLabel(item.id, item.label) ?? item.ariaLabel"
          @click="isInteractiveCenterChip(item.id) ? onCenterChipClick(item.id) : undefined"
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
          <span
            v-else-if="item.id === 'watch-offline'"
            class="status-bar-mockup__icon status-bar-mockup__icon--watch-offline"
            aria-hidden="true"
          />
          <span class="status-bar-mockup__chip-label">{{ item.label }}</span>
        </component>

        <span class="status-bar-mockup__rail" aria-hidden="true" />

        <div
          v-if="operatorZone"
          class="status-bar-mockup__chip status-bar-mockup__chip--operator"
        >
          <span class="status-bar-mockup__icon status-bar-mockup__icon--operator" aria-hidden="true" />
          <span class="status-bar-mockup__chip-label">{{ operatorZone.label }}</span>
        </div>

        <div v-if="previewServers.hasServers.value" class="status-bar-mockup__preview">
          <button
            type="button"
            class="status-bar-mockup__chip status-bar-mockup__chip--preview"
            ref="previewChipRef"
            :aria-expanded="previewServers.panelOpen.value"
            :title="`${previewServers.count.value} sandbox preview server(s) running \u2014 click to view or stop`"
            @click="togglePreviewPanel()"
          >
            <span class="status-bar-mockup__preview-dot" aria-hidden="true" />
            <span class="status-bar-mockup__chip-label">
              Preview {{ previewServers.count.value > 1 ? `\u00d7${previewServers.count.value}` : '' }}
            </span>
          </button>

          <Teleport to="body">
          <div
            v-if="previewServers.panelOpen.value"
            class="status-bar-mockup__preview-panel"
            :style="{ left: `${previewAnchor.left}px`, bottom: `${previewAnchor.bottom}px` }"
          >
            <div class="status-bar-mockup__preview-head">
              <span>Sandbox preview servers</span>
              <button
                type="button"
                class="status-bar-mockup__preview-stop"
                :disabled="previewServers.pending.value"
                @click="previewServers.stopAll()"
              >Stop all</button>
            </div>
            <div
              v-for="server in previewServers.servers.value"
              :key="server.port"
              class="status-bar-mockup__preview-row"
            >
              <a :href="server.url" target="_blank" rel="noopener noreferrer">{{ server.url }}</a>
              <span class="status-bar-mockup__preview-meta">
                pid {{ server.pid }} \u00b7 {{ server.managed ? 'managed' : 'orphan' }}
              </span>
              <button
                type="button"
                class="status-bar-mockup__preview-stop"
                :disabled="previewServers.pending.value"
                :title="`Stop the server on port ${server.port}`"
                @click="previewServers.stop(server.port)"
              >Stop</button>
            </div>
            <p v-if="previewServers.error.value" class="status-bar-mockup__preview-error">
              {{ previewServers.error.value }}
            </p>
          </div>
          </Teleport>
        </div>

        <button
          type="button"
          class="status-bar-mockup__chip status-bar-mockup__chip--standup"
          aria-label="Generate a fresh VAXON fleet report"
          title="Generate a fresh fleet report (REPORT)"
          @click="onOpenStandup"
        >
          <span class="status-bar-mockup__icon status-bar-mockup__icon--kairo" aria-hidden="true" />
          <span class="status-bar-mockup__chip-label">Fleet report</span>
        </button>

        <button
          v-if="shell.showKairoBriefingAttention"
          type="button"
          class="status-bar-mockup__chip status-bar-mockup__chip--kairo-briefing"
          :class="{
            'status-bar-mockup__chip--kairo-warning':
              shell.kairoBriefingAttention.severity === 'warning',
          }"
          :aria-label="`${shell.kairoBriefingAttentionLabel}. View the latest operator briefing; this does not generate a new report.`"
          :title="`${shell.kairoBriefingAttentionLabel} · View latest briefing (no new report)`"
          @click="shell.focusKairoBriefing()"
        >
          <span class="status-bar-mockup__kairo-pulse" aria-hidden="true" />
          <span class="status-bar-mockup__icon status-bar-mockup__icon--kairo" aria-hidden="true" />
          <span class="status-bar-mockup__chip-label">
            View <PersonaTitle suffix="Briefing" mark-size="xs" />
          </span>
          <span class="status-bar-mockup__chip-badge" aria-hidden="true">
            {{ shell.kairoBriefingAttention.badgeCount }}
          </span>
        </button>

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
    </div>
  </footer>
</template>

<style scoped>
.status-bar-mockup__preview {
  position: relative;
}

.status-bar-mockup__preview-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(74, 222, 128);
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.8);
}

.status-bar-mockup__preview-panel {
  position: fixed;
  z-index: 200;
  min-width: 20rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid rgba(45, 212, 191, 0.4);
  border-radius: 8px;
  background: rgba(2, 8, 23, 0.97);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  font-size: 0.62rem;
}

.status-bar-mockup__preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
  color: rgba(226, 236, 248, 0.8);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-bar-mockup__preview-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.22rem 0;
}

.status-bar-mockup__preview-row a {
  color: rgb(134, 239, 172);
  text-decoration: underline;
}

.status-bar-mockup__preview-meta {
  flex: 1;
  color: rgba(226, 236, 248, 0.6);
}

.status-bar-mockup__preview-stop {
  padding: 0.1rem 0.4rem;
  border: 1px solid rgba(248, 113, 113, 0.5);
  border-radius: 4px;
  background: none;
  color: rgb(248, 113, 113);
  cursor: pointer;
  font-size: 0.58rem;
}

.status-bar-mockup__preview-stop:disabled {
  opacity: 0.5;
  cursor: default;
}

.status-bar-mockup__preview-error {
  margin: 0.3rem 0 0;
  color: rgba(254, 243, 199, 0.9);
}
</style>
