<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { useBrainGalaxy } from '../../features/brain-galaxy/use-brain-galaxy';
import GalaxyWorkspacesRail from '../../features/brain-galaxy/GalaxyWorkspacesRail.vue';
import GalaxyIntelligencePanel from '../../features/brain-galaxy/GalaxyIntelligencePanel.vue';
import GalaxySpeechCaptions from '../../features/brain-galaxy/GalaxySpeechCaptions.vue';
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import OperatorEvidencePanel from '../../features/operator-evidence/OperatorEvidencePanel.vue';
import {
  isKairoConversationBusy,
  kairoLastActionTier,
  kairoLastRoutingReceipt,
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
import {
  brainGraphHeadline,
  layoutBrainGraph,
  type BrainGraphNode,
} from '../../lib/operator-brain-graph-view';
import { useShellStore } from '../../stores/shell';

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

function syncGalaxyBottomReserve(): void {
  const stage = galaxyStage.value;
  const hud = bottomHud.value;
  if (!stage) {
    return;
  }
  const reservePx = Math.max(hud?.offsetHeight ?? 0, 92);
  stage.style.setProperty('--galaxy-bottom-reserve', `${reservePx}px`);
}

const snapshot = computed(() => shell.operatorBrainGraph);
const layout = computed(() =>
  layoutBrainGraph(snapshot.value, { width: 640, height: 400 }),
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
const utcClock = ref('');
let clockTimer: number | null = null;

function tickClock(): void {
  utcClock.value = new Date().toISOString().slice(11, 19) + ' UTC';
}

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
const streamWorkspaceId = computed(() => shell.currentWorkspace?.workspace_id ?? null);

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
  tickClock();
  clockTimer = window.setInterval(tickClock, 1000);
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
  if (clockTimer !== null) {
    window.clearInterval(clockTimer);
    clockTimer = null;
  }
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
    :class="[stagePresenceClass, { 'brain-galaxy-stage--vaxon-busy': vaxonBusy }]"
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
        class="brain-galaxy-stage__fallback"
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <line
          v-for="edge in layout.edges"
          :key="edge.edge_id"
          class="operator-brain-graph__edge"
          :class="`operator-brain-graph__edge--${edge.kind}`"
          :x1="edge.x1"
          :y1="edge.y1"
          :x2="edge.x2"
          :y2="edge.y2"
        />
        <g
          v-for="node in layout.nodes"
          :key="node.node_id"
          class="operator-brain-graph__node"
          :class="[
            `operator-brain-graph__node--${node.kind}`,
            `operator-brain-graph__node--${node.tone}`,
          ]"
          :transform="`translate(${node.x}, ${node.y})`"
          @click="handleSvgNodeClick(node)"
        >
          <circle :r="node.radius" />
        </g>
      </svg>

      <p v-if="shell.operatorBrainGraphError" class="brain-galaxy-stage__error" role="alert">
        {{ shell.operatorBrainGraphError }}
      </p>
    </div>

    <GalaxySpeechCaptions />

    <header class="brain-galaxy-stage__hud brain-galaxy-stage__hud--top">
      <div class="brain-galaxy-stage__title-row">
        <span class="brain-galaxy-stage__stats">{{ headline }}</span>
      </div>
    </header>

    <div class="brain-galaxy-stage__hud brain-galaxy-stage__hud--left">
      <GalaxyWorkspacesRail
        :snapshot="snapshot"
        :workspaces="shell.workspaces"
        :selected-id="selectedNode?.node_id ?? null"
        :current-workspace-id="shell.currentWorkspace?.workspace_id ?? null"
        :fleet-health="shell.operatorFleetHealth"
        @select="handleRailSelect"
        @open="handleRailOpen"
      />
    </div>

    <div
      v-if="selectedNode"
      class="brain-galaxy-stage__hud brain-galaxy-stage__hud--inspector"
    >
      <OperatorEvidencePanel
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
    </div>

    <aside class="brain-galaxy-stage__hud brain-galaxy-stage__hud--right">
      <GalaxyIntelligencePanel
        :presence-phase="presence.phase"
        :routing-receipt="kairoLastRoutingReceipt"
      />
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
          <time>{{ utcClock }}</time>
        </div>
      </div>
    </footer>

    <Teleport defer to="#status-bar-galaxy-actions">
      <div class="status-bar-mockup__galaxy-actions-inner" role="group" aria-label="Galaxy view controls">
        <button
          type="button"
          class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
          title="Fit camera and clear selection"
          @click="resetView"
        >
          <span class="status-bar-mockup__chip-label">Fit</span>
        </button>
        <button
          type="button"
          class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
          title="Switch to grid mission control"
          @click="emit('switchGrid')"
        >
          <span class="status-bar-mockup__chip-label">Grid</span>
        </button>
        <button
          type="button"
          class="status-bar-mockup__chip status-bar-mockup__chip--galaxy"
          :class="{ 'status-bar-mockup__chip--galaxy-accent': !props.terminalVisible }"
          :title="props.terminalVisible ? 'Hide terminal' : 'Show terminal'"
          @click="emit('toggleTerminal')"
        >
          <span
            class="status-bar-mockup__dot"
            :class="{ 'status-bar-mockup__dot--warn': !props.terminalVisible }"
            aria-hidden="true"
          />
          <span class="status-bar-mockup__chip-label">Terminal</span>
        </button>
      </div>
    </Teleport>
  </section>
</template>
