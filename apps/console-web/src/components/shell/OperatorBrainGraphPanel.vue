<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, Transition } from 'vue';

import { useBrainGalaxy } from '../../features/brain-galaxy/use-brain-galaxy';
import GalaxyWorkspacesRail from '../../features/brain-galaxy/GalaxyWorkspacesRail.vue';
import GalaxyPanelResizeHandle from '../../features/brain-galaxy/GalaxyPanelResizeHandle.vue';
import GalaxyStatusBarActions from '../../features/brain-galaxy/GalaxyStatusBarActions.vue';
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import OperatorEvidencePanel from '../../features/operator-evidence/OperatorEvidencePanel.vue';
import {
  isKairoConversationBusy,
  kairoLastActionTier,
} from '../../features/kairo-conversation/kairo-conversation-state';
import { kairoCaptureCapturing } from '../../features/kairo-conversation/kairo-shared-speech-capture';
import {
  galaxyInspectorCopy,
  galaxyLegendItems,
  galaxyNodeCounts,
  galaxyTopHubs,
  resolveGalaxyWorkspaceNavigation,
} from '../../features/brain-galaxy/brain-galaxy-hud-view';
import type { GalaxyMockupRailItem } from '../../features/brain-galaxy/galaxy-mockup-rail-view';
import { setBrainGalaxyConversationFocus } from '../../features/brain-galaxy/brain-galaxy-focus';
import { resolveBrainGalaxyNodeSelection } from '../../features/brain-galaxy/brain-galaxy-node-selection';
import { useGalaxySpeechWorkspaceCollapse } from '../../features/brain-galaxy/use-galaxy-speech-workspace-collapse';
import { companyBusyEmployeesCount } from '../../features/workspace-agents/company-roster-busy';
import {
  brainGraphHeadline,
  type BrainGraphNode,
} from '../../lib/operator-brain-graph-view';
import { projectBrainGraph3DToSvg } from '../../features/brain-galaxy/project-brain-graph-3d-to-svg';
import { useShellStore } from '../../stores/shell';
import {
  workbenchTerminalPanelAlive,
  workbenchTerminalPanelAriaLabel,
  workbenchTerminalPanelTitle,
} from '../../lib/workbench-terminal-panel-view';
import { useGalaxyPanelResize } from '../../composables/useGalaxyPanelResize';

const props = defineProps<{
  terminalVisible: boolean;
}>();

const emit = defineEmits<{
  toggleTerminal: [];
  switchGrid: [];
}>();

const shell = useShellStore();
const galaxyHost = ref<HTMLElement | null>(null);
const galaxyStage = ref<HTMLElement | null>(null);
const bottomHud = ref<HTMLElement | null>(null);
const legendOpen = ref(false);
let bottomHudObserver: ResizeObserver | null = null;

const {
  widths: galaxyPanelWidths,
  resizing: galaxyResizing,
  leftCollapsed: galaxyWorkspacesCollapsed,
  toggleLeftCollapsed: toggleGalaxyWorkspacesCollapsed,
  setSpeechCollapseActive: setGalaxySpeechCollapseActive,
  startResize: startGalaxyResize,
  onResizeKeydown: onGalaxyResizeKeydown,
  resetWidth: resetGalaxyWidth,
} = useGalaxyPanelResize({ stageRef: galaxyStage });

function syncGalaxyBottomReserve(): void {
  const stage = galaxyStage.value;
  const hud = bottomHud.value;
  if (!stage) {
    return;
  }
  const reservePx = Math.max(hud?.offsetHeight ?? 0, 92);
  const value = `${reservePx}px`;
  stage.style.setProperty('--galaxy-bottom-reserve', value);
  const workbench = stage.closest('.region-center-workbench') as HTMLElement | null;
  workbench?.style.setProperty('--galaxy-bottom-reserve', value);
}

const snapshot = computed(() => shell.operatorBrainGraph);
const layout = computed(() =>
  projectBrainGraph3DToSvg(snapshot.value, { width: 720, height: 460 }),
);
const headline = computed(() => brainGraphHeadline(snapshot.value));
const legend = computed(() => galaxyLegendItems());
const topHubs = computed(() => galaxyTopHubs(snapshot.value));
const nodeCounts = computed(() => galaxyNodeCounts(snapshot.value));
const graphStats = computed(() => ({
  nodes: snapshot.value?.node_count ?? 0,
  links: snapshot.value?.edge_count ?? 0,
  sources: shell.workspaces.length,
}));

/** Focus a workspace on the map and load its company team — stay on the map. */
function selectWorkspaceCompany(workspaceId: string, nodeId: string, label: string): void {
  setBrainGalaxyConversationFocus({
    nodeId,
    workspaceId,
    signalId: null,
    label,
  });
  shell.setCurrentWorkspace(workspaceId);
}

/** Leave the map and open the workspace coding surface. */
function enterWorkspace(workspaceId: string, nodeId: string, label: string): void {
  selectWorkspaceCompany(workspaceId, nodeId, label);
  shell.setLeftSidebarMode('workspaces');
  shell.setLayoutMode('ide');
}

function handleNodeClick(node: BrainGraphNode): void {
  if (node.kind === 'workspace' && node.workspace_id) {
    selectWorkspaceCompany(
      node.workspace_id,
      node.node_id,
      node.label || node.workspace_id,
    );
    return;
  }
  const selection = resolveBrainGalaxyNodeSelection(node);
  setBrainGalaxyConversationFocus(selection.focus);
}

const pendingApprovals = computed(
  () =>
    shell.operatorBriefing?.pending_approvals.count ??
    shell.runtimeSummary?.approvals.pending_count ??
    0,
);
const criticalSignals = computed(
  () =>
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'critical').length ??
    0,
);
const highSignals = computed(
  () =>
    shell.operatorBriefing?.top_signals.filter((signal) => signal.severity === 'high').length ?? 0,
);
const speechCapturing = kairoCaptureCapturing;
const kairoSpeechActive = computed(() => shell.kairoSpeechActive);
const agentStreamActive = computed(() => shell.agentStreamActive);
const companyBusyCount = computed(() =>
  companyBusyEmployeesCount(shell.companyEmployeesFleet),
);
const fleetActiveRuns = computed(
  () =>
    shell.runtimeSummary?.active_runs?.length ??
    shell.operatorBriefing?.active_runs?.length ??
    0,
);
const streamWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);
useGalaxySpeechWorkspaceCollapse({
  kairoSpeechActive,
  setSpeechCollapseActive: setGalaxySpeechCollapseActive,
});
const terminalRunPhase = computed(() => shell.primaryActiveRun?.phase ?? null);

const terminalDockAlive = computed(
  () => !props.terminalVisible && workbenchTerminalPanelAlive(terminalRunPhase.value),
);

const terminalPanelTitle = computed(() =>
  workbenchTerminalPanelTitle(props.terminalVisible, terminalRunPhase.value),
);

const terminalPanelAriaLabel = computed(() =>
  workbenchTerminalPanelAriaLabel(props.terminalVisible, terminalRunPhase.value),
);

const {
  webglReady,
  webglFailed,
  selectedNode,
  presence,
  resetView,
  clearSelection,
  selectNode,
  focusNode,
} = useBrainGalaxy({
  container: galaxyHost,
  snapshot,
  onNodeClick: handleNodeClick,
  speechCapturing,
  kairoSpeechActive,
  agentStreamActive,
  streamWorkspaceId,
  companyBusyCount,
  fleetActiveRuns,
  pendingApprovals,
  criticalSignals,
  highSignals,
});

const inspector = computed(() => galaxyInspectorCopy(selectedNode.value));
const showLoading = computed(() => !webglReady.value && !webglFailed.value);
const showSvgFallback = computed(() => webglFailed.value);
const vaxonBusy = computed(() => isKairoConversationBusy() || presence.value.busy);
const stagePresenceClass = computed(() => presence.value.stageClass);

function onEscapeClear(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !selectedNode.value) {
    return;
  }
  clearSelection();
}

onMounted(() => {
  // Retry after a prior timeout/error — otherwise the panel stays on
  // "Loading brain graph…" with a null snapshot forever.
  if (
    shell.operatorBrainGraphLoadState === 'idle' ||
    shell.operatorBrainGraphLoadState === 'error' ||
    (shell.operatorBrainGraphLoadState === 'loaded' && !shell.operatorBrainGraph)
  ) {
    void shell.loadOperatorBrainGraph();
  }
  if (shell.operatorFleetHealthLoadState === 'idle') {
    void shell.loadOperatorFleetHealth();
  }
  if (shell.briefingLoadState === 'idle') {
    void shell.loadOperatorBriefing();
  }
  syncGalaxyBottomReserve();
  if (typeof ResizeObserver !== 'undefined' && bottomHud.value) {
    bottomHudObserver = new ResizeObserver(() => {
      syncGalaxyBottomReserve();
    });
    bottomHudObserver.observe(bottomHud.value);
  }
  window.addEventListener('keydown', onEscapeClear);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscapeClear);
  bottomHudObserver?.disconnect();
  bottomHudObserver = null;
});

watch(
  [() => snapshot.value?.nodes, webglReady],
  ([nodes]) => {
    if (selectedNode.value || !nodes?.length) {
      return;
    }
    const core = nodes.find((node) => node.kind === 'core') ?? null;
    if (core) {
      selectNode(core);
    }
  },
  { immediate: true },
);

function handleRailSelect(item: GalaxyMockupRailItem): void {
  focusNode(item.id);
  if (item.kind === 'workspace' && item.workspace_id) {
    selectWorkspaceCompany(item.workspace_id, item.id, item.label);
    return;
  }
  if (item.workspace_id) {
    shell.setCurrentWorkspace(item.workspace_id);
  }
}

function handleRailOpen(item: GalaxyMockupRailItem): void {
  if (item.kind !== 'workspace' || !item.workspace_id) {
    return;
  }
  enterWorkspace(item.workspace_id, item.id, item.label);
}

function handleSvgNodeClick(node: BrainGraphNode): void {
  selectNode(node);
  handleNodeClick(node);
}

function handleEvidenceWorkspace(workspaceId: string): void {
  const nav = resolveGalaxyWorkspaceNavigation(workspaceId);
  if (!nav) {
    return;
  }
  const label =
    selectedNode.value?.label ??
    topHubs.value.find((hub) => hub.workspace_id === workspaceId)?.label ??
    workspaceId;
  enterWorkspace(nav.workspaceId, `ws_${workspaceId}`, label);
}

function handleEvidenceSignal(signalId: string): void {
  shell.focusAttentionSidebar(signalId);
}

function handleEvidenceHandoff(signal: {
  signal_id: string;
  workspace_id?: string | null;
  title: string;
  summary?: string | null;
  meta?: Record<string, unknown> | null;
}): void {
  void shell.handoffSignalToIde(signal, { autoSubmit: true });
}
</script>

<template>
  <section
    ref="galaxyStage"
    class="brain-galaxy-stage brain-galaxy-stage--mockup"
    :class="[stagePresenceClass, {
      'brain-galaxy-stage--vaxon-busy': vaxonBusy,
      'brain-galaxy-stage--workspaces-collapsed': galaxyWorkspacesCollapsed,
    }]"
    :data-galaxy-presence="presence.phase"
    aria-label="Brain galaxy mission control"
  >
    <div
      ref="galaxyHost"
      class="brain-galaxy-stage__viewport"
      :class="{ 'brain-galaxy-stage__viewport--ready': webglReady }"
      role="img"
      aria-label="3D operator brain galaxy"
    >
      <div v-if="showLoading" class="brain-galaxy-stage__loading">
        <span class="brain-galaxy-stage__loading-orb" aria-hidden="true" />
        <span>Spinning up galaxy…</span>
      </div>

      <svg
        v-if="showSvgFallback"
        class="brain-galaxy-stage__fallback brain-galaxy-stage__fallback--nebula"
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="galaxy-nebula-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="rgba(210, 240, 255, 0.55)" />
            <stop offset="42%" stop-color="rgba(120, 200, 255, 0.22)" />
            <stop offset="100%" stop-color="rgba(4, 10, 18, 0)" />
          </radialGradient>
          <radialGradient id="galaxy-node-core" cx="35%" cy="30%" r="65%">
            <stop offset="0%" stop-color="rgba(230, 248, 255, 0.95)" />
            <stop offset="55%" stop-color="rgba(72, 196, 255, 0.55)" />
            <stop offset="100%" stop-color="rgba(20, 60, 90, 0.85)" />
          </radialGradient>
          <radialGradient id="galaxy-node-signal" cx="35%" cy="30%" r="65%">
            <stop offset="0%" stop-color="rgba(255, 210, 230, 0.95)" />
            <stop offset="60%" stop-color="rgba(255, 90, 150, 0.7)" />
            <stop offset="100%" stop-color="rgba(80, 20, 40, 0.9)" />
          </radialGradient>
          <radialGradient id="galaxy-node-connector" cx="35%" cy="30%" r="65%">
            <stop offset="0%" stop-color="rgba(200, 230, 255, 0.95)" />
            <stop offset="60%" stop-color="rgba(70, 140, 255, 0.75)" />
            <stop offset="100%" stop-color="rgba(20, 40, 90, 0.9)" />
          </radialGradient>
          <filter id="galaxy-soft-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle
          v-for="(star, index) in layout.stars"
          :key="`star-${index}`"
          class="brain-galaxy-stage__fallback-star"
          :cx="star.x"
          :cy="star.y"
          :r="star.r"
          :opacity="star.o"
        />
        <ellipse
          class="brain-galaxy-stage__fallback-nebula"
          :cx="layout.nebula.cx"
          :cy="layout.nebula.cy"
          :rx="layout.nebula.rx"
          :ry="layout.nebula.ry"
          fill="url(#galaxy-nebula-glow)"
        />
        <line
          v-for="edge in layout.edges"
          :key="edge.edge_id"
          class="operator-brain-graph__edge operator-brain-graph__edge--nebula"
          :class="`operator-brain-graph__edge--${edge.kind}`"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
        />
        <g
          v-for="node in layout.nodes"
          :key="node.node_id"
          class="operator-brain-graph__node operator-brain-graph__node--nebula"
          :class="[
            `operator-brain-graph__node--${node.kind}`,
            `operator-brain-graph__node--${node.tone}`,
          ]"
          :transform="`translate(${node.x}, ${node.y})`"
          @click="handleSvgNodeClick(node)"
        >
          <circle
            class="operator-brain-graph__node-glow"
            :r="node.radius * 1.85"
            filter="url(#galaxy-soft-glow)"
          />
          <circle
            class="operator-brain-graph__node-body"
            :r="node.radius"
            :fill="
              node.kind === 'signal'
                ? 'url(#galaxy-node-signal)'
                : node.kind === 'connector'
                  ? 'url(#galaxy-node-connector)'
                  : 'url(#galaxy-node-core)'
            "
          />
          <g v-if="node.showLabel" class="operator-brain-graph__node-label-chip">
            <rect
              :x="-(Math.min(node.label.length, 16) * 3.1 + 8) / 2"
              :y="-node.radius - 18"
              :width="Math.min(node.label.length, 16) * 3.1 + 8"
              height="12"
              rx="3"
            />
            <text :y="-node.radius - 9" text-anchor="middle">
              {{ node.label.slice(0, 16) }}
            </text>
          </g>
        </g>
      </svg>

      <p v-if="shell.operatorBrainGraphError" class="brain-galaxy-stage__error" role="alert">
        {{ shell.operatorBrainGraphError }}
      </p>
    </div>

    <header class="brain-galaxy-stage__hud brain-galaxy-stage__hud--top">
      <div class="brain-galaxy-stage__title-row">
        <span class="brain-galaxy-stage__stats">{{ headline }}</span>
      </div>
    </header>

    <div
      class="brain-galaxy-stage__hud brain-galaxy-stage__hud--left"
      :class="{ 'brain-galaxy-stage__hud--left-collapsed': galaxyWorkspacesCollapsed }"
    >
      <GalaxyPanelResizeHandle
        v-if="!galaxyWorkspacesCollapsed"
        edge="right"
        label="Resize workspaces rail"
        :value-min="180"
        :value-max="420"
        :value-now="galaxyPanelWidths.left"
        @mousedown="startGalaxyResize('left', 'left', $event)"
        @keydown="onGalaxyResizeKeydown('left', 'left', $event)"
        @dblclick="resetGalaxyWidth('left')"
      />
      <GalaxyWorkspacesRail
        :snapshot="snapshot"
        :workspaces="shell.workspaces"
        :selected-id="selectedNode?.node_id ?? null"
        :current-workspace-id="shell.currentWorkspace?.workspace_id ?? null"
        :fleet-health="shell.operatorFleetHealth"
        :collapsed="galaxyWorkspacesCollapsed"
        @select="handleRailSelect"
        @open="handleRailOpen"
        @toggle-collapse="toggleGalaxyWorkspacesCollapsed"
      />
    </div>

    <div
      v-if="selectedNode"
      class="brain-galaxy-stage__hud brain-galaxy-stage__hud--inspector"
      :class="{ 'galaxy-panel--resizing': galaxyResizing === 'inspector' }"
    >
      <GalaxyPanelResizeHandle
        edge="left"
        label="Resize inspector panel"
        :value-min="260"
        :value-max="520"
        :value-now="galaxyPanelWidths.inspector"
        @mousedown="startGalaxyResize('inspector', 'right', $event)"
        @keydown="onGalaxyResizeKeydown('inspector', 'right', $event)"
        @dblclick="resetGalaxyWidth('inspector')"
      />
      <Transition name="motion-panel">
        <OperatorEvidencePanel
          :key="selectedNode.node_id"
          :node-id="selectedNode.node_id"
          :fallback-title="inspector.title"
          :fallback-body="inspector.body"
          :fallback-hint="inspector.hint"
          :pending-approvals="pendingApprovals"
          :run-phase="shell.primaryActiveRun?.phase ?? null"
          :action-tier="kairoLastActionTier"
          :execution-access="shell.agentExecutionAccess"
          :workspace-selected="Boolean(shell.currentWorkspace?.workspace_id)"
          @dismiss="clearSelection"
          @open-workspace="handleEvidenceWorkspace"
          @open-signal="handleEvidenceSignal"
          @handoff-signal="handleEvidenceHandoff"
        />
      </Transition>
    </div>

    <aside
      class="brain-galaxy-stage__hud brain-galaxy-stage__hud--right"
      :class="{ 'galaxy-panel--resizing': galaxyResizing === 'right' }"
    >
      <GalaxyPanelResizeHandle
        edge="left"
        label="Resize intelligence panel"
        :value-min="180"
        :value-max="360"
        :value-now="galaxyPanelWidths.right"
        @mousedown="startGalaxyResize('right', 'right', $event)"
        @keydown="onGalaxyResizeKeydown('right', 'right', $event)"
        @dblclick="resetGalaxyWidth('right')"
      />
      <!-- Floating VAXON orb is hosted by VoiceOrbHost on Brain Graph. -->
      <button
        type="button"
        class="brain-galaxy-stage__legend-toggle"
        :aria-expanded="legendOpen"
        @click="legendOpen = !legendOpen"
      >
        Legend
      </button>
      <ul v-if="legendOpen" class="brain-galaxy-stage__legend">
        <li v-for="item in legend" :key="item.kind">
          <span class="brain-galaxy-stage__legend-dot" :style="{ background: item.color }" />
          <span>{{ item.label }}</span>
          <strong v-if="nodeCounts[item.kind]">{{ nodeCounts[item.kind] }}</strong>
        </li>
      </ul>
    </aside>

    <footer ref="bottomHud" class="brain-galaxy-stage__hud brain-galaxy-stage__hud--bottom galaxy-operator-console">
      <div class="galaxy-operator-console__brand">
        <span class="galaxy-operator-console__mark" aria-hidden="true">⬡</span>
        <div>
          <strong>VAXON // OPERATOR CONSOLE</strong>
          <span class="galaxy-operator-console__online">● ONLINE</span>
        </div>
      </div>
      <div class="galaxy-operator-console__command">
        <KairoConversationBar />
      </div>
      <div class="galaxy-operator-console__footer-right">
        <div class="galaxy-operator-console__stats" aria-label="Graph stats">
          <div>
            <span>NODES</span>
            <strong>{{ graphStats.nodes.toLocaleString() }}</strong>
          </div>
          <div>
            <span>LINKS</span>
            <strong>{{ graphStats.links.toLocaleString() }}</strong>
          </div>
          <div>
            <span>SOURCES</span>
            <strong>{{ graphStats.sources.toLocaleString() }}</strong>
          </div>
        </div>
      </div>
    </footer>

    <Teleport defer to="#status-bar-galaxy-actions">
      <GalaxyStatusBarActions
        :terminal-visible="props.terminalVisible"
        :terminal-dock-alive="terminalDockAlive"
        :terminal-run-phase="terminalRunPhase"
        :terminal-panel-title="terminalPanelTitle"
        :terminal-panel-aria-label="terminalPanelAriaLabel"
        @reset-view="resetView"
        @switch-grid="emit('switchGrid')"
        @toggle-terminal="emit('toggleTerminal')"
      />
    </Teleport>
  </section>
</template>
