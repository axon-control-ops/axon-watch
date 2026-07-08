<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { useBrainGalaxy } from '../../features/brain-galaxy/use-brain-galaxy';
import KairoGalaxyOrb from '../../features/brain-galaxy/KairoGalaxyOrb.vue';
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import {
  isKairoConversationBusy,
} from '../../features/kairo-conversation/kairo-conversation-state';
import {
  galaxyInspectorCopy,
  galaxyLegendItems,
  galaxyNodeCounts,
  galaxyTopHubs,
} from '../../features/brain-galaxy/brain-galaxy-hud-view';
import {
  brainGraphHeadline,
  layoutBrainGraph,
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
const legendOpen = ref(false);

onMounted(() => {
  if (shell.operatorBrainGraphLoadState === 'idle') {
    void shell.loadOperatorBrainGraph();
  }
});

const snapshot = computed(() => shell.operatorBrainGraph);
const layout = computed(() =>
  layoutBrainGraph(snapshot.value, { width: 640, height: 400 }),
);
const headline = computed(() => brainGraphHeadline(snapshot.value));
const legend = computed(() => galaxyLegendItems());
const topHubs = computed(() => galaxyTopHubs(snapshot.value));
const nodeCounts = computed(() => galaxyNodeCounts(snapshot.value));

function handleNodeClick(node: { kind: string; workspace_id: string | null; node_id: string }): void {
  if (node.kind === 'workspace' && node.workspace_id) {
    shell.setCurrentWorkspace(node.workspace_id);
    return;
  }
  if (node.kind === 'signal') {
    shell.focusAttentionSidebar(node.node_id.replace(/^sig_/, ''));
  }
}

const { webglReady, webglFailed, selectedNode, resetView, focusNode } = useBrainGalaxy({
  container: galaxyHost,
  snapshot,
  onNodeClick: handleNodeClick,
});

const inspector = computed(() => galaxyInspectorCopy(selectedNode.value));
const showLoading = computed(() => !webglReady.value && !webglFailed.value);
const showSvgFallback = computed(() => webglFailed.value);
const vaxonBusy = computed(() => isKairoConversationBusy());

function handleHubClick(hub: { node_id: string; workspace_id: string | null }): void {
  focusNode(hub.node_id);
  if (hub.workspace_id) {
    shell.setCurrentWorkspace(hub.workspace_id);
  }
}
</script>

<template>
  <section
    class="brain-galaxy-stage"
    :class="{ 'brain-galaxy-stage--vaxon-busy': vaxonBusy }"
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
          @click="handleNodeClick(node)"
        >
          <circle :r="node.radius" />
        </g>
      </svg>

      <p v-if="shell.operatorBrainGraphError" class="brain-galaxy-stage__error" role="alert">
        {{ shell.operatorBrainGraphError }}
      </p>
    </div>

    <header class="brain-galaxy-stage__hud brain-galaxy-stage__hud--top">
      <div class="brain-galaxy-stage__title-row">
        <p class="brain-galaxy-stage__eyebrow">Mission control</p>
        <h2 class="brain-galaxy-stage__title">Brain galaxy</h2>
        <span class="brain-galaxy-stage__stats">{{ headline }}</span>
      </div>
      <div class="brain-galaxy-stage__top-actions">
        <button type="button" class="brain-galaxy-stage__chip" title="Reset camera" @click="resetView">
          Fit
        </button>
        <button type="button" class="brain-galaxy-stage__chip" @click="emit('switchGrid')">
          Grid
        </button>
        <button
          type="button"
          class="brain-galaxy-stage__chip"
          :class="{ 'brain-galaxy-stage__chip--accent': !props.terminalVisible }"
          @click="emit('toggleTerminal')"
        >
          {{ props.terminalVisible ? 'Terminal' : 'Terminal +' }}
        </button>
      </div>
    </header>

    <aside class="brain-galaxy-stage__hud brain-galaxy-stage__hud--left">
      <p class="brain-galaxy-stage__panel-label">Workspaces</p>
      <ul class="brain-galaxy-stage__hub-list">
        <li v-for="hub in topHubs" :key="hub.node_id">
          <button
            type="button"
            class="brain-galaxy-stage__hub"
            :class="[
              `brain-galaxy-stage__hub--${hub.tone}`,
              { 'brain-galaxy-stage__hub--active': selectedNode?.node_id === hub.node_id },
            ]"
            @click="handleHubClick(hub)"
          >
            <span class="brain-galaxy-stage__hub-dot" aria-hidden="true" />
            <span class="brain-galaxy-stage__hub-copy">
              <strong>{{ hub.label }}</strong>
              <span>{{ hub.detail }}</span>
            </span>
          </button>
        </li>
      </ul>
    </aside>

    <aside
      v-if="selectedNode"
      class="brain-galaxy-stage__hud brain-galaxy-stage__hud--inspector"
    >
      <p class="brain-galaxy-stage__inspector-title">{{ inspector.title }}</p>
      <p class="brain-galaxy-stage__inspector-body">{{ inspector.body }}</p>
      <p class="brain-galaxy-stage__inspector-hint">{{ inspector.hint }}</p>
    </aside>

    <aside class="brain-galaxy-stage__hud brain-galaxy-stage__hud--right">
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

    <footer class="brain-galaxy-stage__hud brain-galaxy-stage__hud--bottom">
      <KairoConversationBar />
    </footer>

    <KairoGalaxyOrb />
  </section>
</template>
