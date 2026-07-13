import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch, type Ref } from 'vue';

import type { BrainGraphNode, BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import {
  isKairoConversationBusy,
  kairoConversationPhase,
} from '../kairo-conversation/kairo-conversation-state';
import { BrainGalaxyScene } from './brain-galaxy-scene';
import {
  resolveGalaxyPresence,
  type GalaxyPresencePhase,
  type GalaxyPresenceResolved,
} from './galaxy-presence-state';

export type UseBrainGalaxyOptions = {
  container: Ref<HTMLElement | null>;
  snapshot: Ref<BrainGraphSnapshot | null>;
  onNodeClick: (node: BrainGraphNode) => void;
  speechCapturing?: Ref<boolean>;
  kairoSpeechActive?: Ref<boolean>;
  agentStreamActive?: Ref<boolean>;
  pendingApprovals?: Ref<number>;
  criticalSignals?: Ref<number>;
  highSignals?: Ref<number>;
};

export function useBrainGalaxy(options: UseBrainGalaxyOptions): {
  webglReady: Ref<boolean>;
  webglFailed: Ref<boolean>;
  selectedNode: Ref<BrainGraphNode | null>;
  presence: Ref<GalaxyPresenceResolved>;
  presencePhase: Ref<GalaxyPresencePhase>;
  resetView: () => void;
  clearSelection: () => void;
  focusNode: (nodeId: string) => void;
  selectNode: (node: BrainGraphNode) => void;
} {
  const webglReady = ref(false);
  const webglFailed = ref(false);
  const selectedNode = ref<BrainGraphNode | null>(null);
  const sceneRef = shallowRef<BrainGalaxyScene | null>(null);

  const presence = computed(() =>
    resolveGalaxyPresence({
      selectedNodeId: selectedNode.value?.node_id ?? null,
      selectedNodeKind: selectedNode.value?.kind ?? null,
      conversationPhase: kairoConversationPhase.value,
      speechCapturing: options.speechCapturing?.value ?? false,
      kairoSpeechActive: options.kairoSpeechActive?.value ?? false,
      agentStreamActive: options.agentStreamActive?.value ?? false,
      pendingApprovals: options.pendingApprovals?.value ?? 0,
      criticalSignals: options.criticalSignals?.value ?? 0,
      highSignals: options.highSignals?.value ?? 0,
    }),
  );

  const presencePhase = computed(() => presence.value.phase);

  function clearSelection(): void {
    selectedNode.value = null;
    sceneRef.value?.setSelectedNode(null);
  }

  function resetView(): void {
    clearSelection();
    sceneRef.value?.resetView();
  }

  function selectNode(node: BrainGraphNode): void {
    selectedNode.value = node;
    sceneRef.value?.setSelectedNode(node.node_id);
    options.onNodeClick(node);
  }

  function focusNode(nodeId: string): void {
    sceneRef.value?.focusNode(nodeId);
    const node = options.snapshot.value?.nodes.find((entry) => entry.node_id === nodeId) ?? null;
    if (node) {
      selectNode(node);
      return;
    }
    clearSelection();
  }

  function syncPresenceToScene(): void {
    const scene = sceneRef.value;
    if (!scene) {
      return;
    }
    scene.setVaxonCoreMode(presence.value.coreOrbMode);
  }

  function mountScene(): void {
    const container = options.container.value;
    if (!container || sceneRef.value || webglFailed.value || webglReady.value) {
      return;
    }

    if (container.clientHeight < 8) {
      window.requestAnimationFrame(mountScene);
      return;
    }

    if (!BrainGalaxyScene.isWebGLAvailable()) {
      webglFailed.value = true;
      return;
    }

    const scene = new BrainGalaxyScene(
      container,
      (node) => {
        selectedNode.value = node;
        options.onNodeClick(node);
      },
      () => {
        selectedNode.value = null;
      },
    );
    const ok = scene.init();
    if (!ok) {
      webglFailed.value = true;
      scene.dispose();
      return;
    }

    sceneRef.value = scene;
    scene.setSnapshot(options.snapshot.value);
    scene.setVaxonBusy(isKairoConversationBusy());
    syncPresenceToScene();
    if (selectedNode.value) {
      scene.setSelectedNode(selectedNode.value.node_id);
    }
    webglReady.value = true;
  }

  onMounted(() => {
    void nextTick(() => {
      mountScene();
    });
  });

  watch(
    () => options.snapshot.value,
    (snapshot) => {
      sceneRef.value?.setSnapshot(snapshot);
      if (
        selectedNode.value &&
        !snapshot?.nodes.some((node) => node.node_id === selectedNode.value?.node_id)
      ) {
        selectedNode.value = null;
      }
    },
  );

  watch(
    presence,
    () => {
      syncPresenceToScene();
    },
    { immediate: true },
  );

  watch(
    kairoConversationPhase,
    () => {
      sceneRef.value?.setVaxonBusy(isKairoConversationBusy());
      syncPresenceToScene();
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    sceneRef.value?.dispose();
    sceneRef.value = null;
  });

  return {
    webglReady,
    webglFailed,
    selectedNode,
    presence,
    presencePhase,
    resetView,
    clearSelection,
    focusNode,
    selectNode,
  };
}
