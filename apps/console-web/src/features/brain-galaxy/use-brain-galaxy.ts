import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch, type Ref } from 'vue';

import type { BrainGraphNode, BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import { BrainGalaxyScene } from './brain-galaxy-scene';

export type UseBrainGalaxyOptions = {
  container: Ref<HTMLElement | null>;
  snapshot: Ref<BrainGraphSnapshot | null>;
  onNodeClick: (node: BrainGraphNode) => void;
};

export function useBrainGalaxy(options: UseBrainGalaxyOptions): {
  webglReady: Ref<boolean>;
  webglFailed: Ref<boolean>;
  selectedNode: Ref<BrainGraphNode | null>;
  resetView: () => void;
  focusNode: (nodeId: string) => void;
} {
  const webglReady = ref(false);
  const webglFailed = ref(false);
  const selectedNode = ref<BrainGraphNode | null>(null);
  const sceneRef = shallowRef<BrainGalaxyScene | null>(null);

  function resetView(): void {
    selectedNode.value = null;
    sceneRef.value?.setSelectedNode(null);
    sceneRef.value?.resetView();
  }

  function focusNode(nodeId: string): void {
    sceneRef.value?.focusNode(nodeId);
    const node = options.snapshot.value?.nodes.find((entry) => entry.node_id === nodeId) ?? null;
    selectedNode.value = node;
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

    const scene = new BrainGalaxyScene(container, (node) => {
      selectedNode.value = node;
      options.onNodeClick(node);
    });
    const ok = scene.init();
    if (!ok) {
      webglFailed.value = true;
      scene.dispose();
      return;
    }

    sceneRef.value = scene;
    scene.setSnapshot(options.snapshot.value);
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

  onBeforeUnmount(() => {
    sceneRef.value?.dispose();
    sceneRef.value = null;
  });

  return { webglReady, webglFailed, selectedNode, resetView, focusNode };
}
