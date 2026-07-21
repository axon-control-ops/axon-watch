import {
  Group,
  Line,
  MeshStandardMaterial,
  PerspectiveCamera,
  Raycaster,
  Scene,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

import type { BrainGraphNode, BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import { GALAXY_BACKGROUND } from './brain-galaxy-colors';
import { applyGalaxySelectionFocus } from './brain-galaxy-selection-effects';
import {
  animateGalaxyAmbience,
  buildAnimatedStarfield,
  buildGalaxyLighting,
  configureGalaxyRenderer,
} from './galaxy-ambient-effects';
import {
  layoutBrainGraph3D,
  type BrainGraphLayout3D,
} from './layout-brain-graph-3d';
import { animateLiveEdge, buildLiveEdge } from './network-edge-effects';
import {
  animateSpecialtyDispatchFilament,
  buildSpecialtyDispatchFilament,
  disposeSpecialtyDispatchFilament,
  type SpecialtyDispatchFilament,
} from './specialty-dispatch-filament';
import { animateVaxonCoreOrb } from './vaxon-core-orb-3d';
import { animateWorkspaceNode } from './workspace-node-effects';
import type { GalaxyCoreOrbMode } from './galaxy-presence-state';
import { presenceAmpForCoreMode } from './galaxy-presence-state';
import { GALAXY_FOCUS_CAMERA_OFFSET, galaxyFocusCameraPosition } from './brain-galaxy-focus-camera';
import { buildGalaxyNodeMesh, type GalaxyNodeMesh } from './brain-galaxy-node-mesh';

export type BrainGalaxyNodeClickHandler = (node: BrainGraphNode) => void;
export type BrainGalaxyClearSelectionHandler = () => void;

type NodeMesh = GalaxyNodeMesh;

export class BrainGalaxyScene {
  private readonly container: HTMLElement;
  private readonly onNodeClick: BrainGalaxyNodeClickHandler;
  private readonly onClearSelection: BrainGalaxyClearSelectionHandler | null;
  private renderer: WebGLRenderer | null = null;
  private scene: Scene | null = null;
  private camera: PerspectiveCamera | null = null;
  private controls: OrbitControls | null = null;
  private graphGroup: Group | null = null;
  private starfield: Group | null = null;
  private labelRenderer: CSS2DRenderer | null = null;
  private nodeMeshes: NodeMesh[] = [];
  private liveEdges: Line[] = [];
  private animationId = 0;
  private layout: BrainGraphLayout3D = { nodes: [], edges: [] };
  private clock = 0;
  private disposed = false;
  private readonly raycaster = new Raycaster();
  private readonly pointer = new Vector2();
  private resizeObserver: ResizeObserver | null = null;
  private selectedNodeId: string | null = null;
  private selectedWorkspaceId: string | null = null;
  private focusedNodeIds = new Set<string>();
  private presenceAmp = 0;
  private voiceEnergy = 0;
  private agentStreamActive = false;
  private streamWorkspaceId: string | null = null;
  private vaxonCoreMode: GalaxyCoreOrbMode = 'idle';
  private specialtyFx: SpecialtyDispatchFilament | null = null;
  private readonly defaultCameraPosition = new Vector3(
    GALAXY_FOCUS_CAMERA_OFFSET.x,
    GALAXY_FOCUS_CAMERA_OFFSET.y,
    GALAXY_FOCUS_CAMERA_OFFSET.z,
  );
  private readonly defaultTarget = new Vector3(0, 0, 0);

  constructor(
    container: HTMLElement,
    onNodeClick: BrainGalaxyNodeClickHandler,
    onClearSelection?: BrainGalaxyClearSelectionHandler,
  ) {
    this.container = container;
    this.onNodeClick = onNodeClick;
    this.onClearSelection = onClearSelection ?? null;
  }

  static isWebGLAvailable(): boolean {
    try {
      const canvas = document.createElement('canvas');
      return Boolean(
        canvas.getContext('webgl2') ?? canvas.getContext('webgl'),
      );
    } catch {
      return false;
    }
  }

  init(): boolean {
    if (this.disposed || !BrainGalaxyScene.isWebGLAvailable()) {
      return false;
    }

    const width = this.container.clientWidth || 640;
    const height = this.container.clientHeight || 420;

    this.renderer = new WebGLRenderer({ antialias: true, alpha: true });
    configureGalaxyRenderer(this.renderer);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(width, height, false);
    this.renderer.setClearColor(GALAXY_BACKGROUND, 1);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new Scene();

    this.camera = new PerspectiveCamera(42, width / height, 0.1, 100);
    this.camera.position.copy(this.defaultCameraPosition);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.setSize(width, height);
    const labelRoot = this.labelRenderer.domElement;
    labelRoot.className = 'brain-galaxy-stage__labels';
    labelRoot.style.position = 'absolute';
    labelRoot.style.inset = '0';
    labelRoot.style.zIndex = '2';
    labelRoot.style.pointerEvents = 'none';
    labelRoot.style.overflow = 'hidden';
    this.container.appendChild(labelRoot);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 0.38;
    this.controls.minDistance = 2.8;
    this.controls.maxDistance = 11;
    this.controls.enablePan = false;

    this.scene.add(buildGalaxyLighting());

    this.graphGroup = new Group();
    this.scene.add(this.graphGroup);
    this.starfield = buildAnimatedStarfield();
    this.scene.add(this.starfield);

    this.renderer.domElement.addEventListener('click', this.handleClick);
    this.renderer.domElement.addEventListener('pointermove', this.handlePointerMove);

    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(this.container);

    this.animate();
    return true;
  }

  setSnapshot(snapshot: BrainGraphSnapshot | null): void {
    if (!this.graphGroup || this.disposed) {
      return;
    }
    this.layout = layoutBrainGraph3D(snapshot);
    this.rebuildGraph();
    if (this.selectedNodeId) {
      this.applySelectionHighlight(this.selectedNodeId);
    }
  }

  resetView(): void {
    if (!this.camera || !this.controls) {
      return;
    }
    this.camera.position.copy(this.defaultCameraPosition);
    this.controls.target.copy(this.defaultTarget);
    this.controls.autoRotate = true;
    this.controls.update();
  }

  focusNode(nodeId: string): void {
    const mesh = this.nodeMeshes.find((entry) => entry.userData.node.node_id === nodeId);
    if (!mesh || !this.camera || !this.controls) {
      return;
    }
    this.controls.autoRotate = false;
    this.controls.target.set(mesh.position.x, mesh.position.y, mesh.position.z);
    // Keep the default orbit distance so workspace focus frames the node
    // without filling the viewport (the old +2.8 Z dolly made orbs look giant).
    const focusCamera = galaxyFocusCameraPosition(mesh.position);
    this.camera.position.set(focusCamera.x, focusCamera.y, focusCamera.z);
    this.controls.update();
    this.setSelectedNode(nodeId);
  }

  setSelectedNode(nodeId: string | null): void {
    this.selectedNodeId = nodeId;
    this.applySelectionHighlight(nodeId);
  }

  /** Graph amp only — does not override presence-owned core mode. */
  setVaxonBusy(busy: boolean): void {
    if (busy && this.presenceAmp < 1) {
      this.presenceAmp = 1;
    } else if (!busy) {
      this.presenceAmp = presenceAmpForCoreMode(this.vaxonCoreMode);
    }
  }

  setVaxonCoreMode(mode: GalaxyCoreOrbMode): void {
    this.vaxonCoreMode = mode;
    this.presenceAmp = presenceAmpForCoreMode(mode);
  }

  setVoiceEnergy(energy: number): void {
    this.voiceEnergy = Math.max(0, Math.min(1.4, energy));
  }

  setAgentStream(active: boolean, workspaceId: string | null = null): void {
    this.agentStreamActive = active;
    this.streamWorkspaceId = workspaceId;
  }

  playSpecialtyDispatch(workspaceId: string, label: string): void {
    if (!this.scene || this.disposed) {
      return;
    }
    const target = this.nodeMeshes.find(
      (mesh) =>
        mesh.userData.node.kind === 'workspace' &&
        mesh.userData.node.workspace_id === workspaceId,
    );
    if (!target) {
      return;
    }
    const core = this.nodeMeshes.find((mesh) => mesh.userData.node.kind === 'core');
    this.clearSpecialtyDispatch();
    this.specialtyFx = buildSpecialtyDispatchFilament({
      from: core?.position ?? new Vector3(0, 0, 0),
      to: target.position,
      label,
    });
    this.scene.add(this.specialtyFx.group);
    this.focusNode(target.userData.node.node_id);
  }

  clearSpecialtyDispatch(): void {
    if (!this.specialtyFx) {
      return;
    }
    disposeSpecialtyDispatchFilament(this.specialtyFx);
    this.specialtyFx = null;
  }

  private applySelectionHighlight(nodeId: string | null): void {
    const focus = applyGalaxySelectionFocus(
      this.nodeMeshes,
      this.liveEdges,
      this.layout.edges,
      nodeId,
    );
    this.selectedWorkspaceId = focus.selectedWorkspaceId;
    this.focusedNodeIds = focus.focusedNodeIds;
  }

  dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.animationId);
    this.clearSpecialtyDispatch();

    if (this.renderer) {
      this.renderer.domElement.removeEventListener('click', this.handleClick);
      this.renderer.domElement.removeEventListener('pointermove', this.handlePointerMove);
    }

    this.resizeObserver?.disconnect();
    this.controls?.dispose();
    this.renderer?.dispose();
    if (this.starfield) {
      this.disposeObjectTree(this.starfield);
      this.scene?.remove(this.starfield);
    }

    if (this.labelRenderer?.domElement.parentElement === this.container) {
      this.container.removeChild(this.labelRenderer.domElement);
    }

    if (this.renderer?.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }

    this.renderer = null;
    this.labelRenderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.graphGroup = null;
    this.starfield = null;
    this.nodeMeshes = [];
    this.liveEdges = [];
  }

  private rebuildGraph(): void {
    if (!this.graphGroup) {
      return;
    }

    while (this.graphGroup.children.length > 0) {
      const child = this.graphGroup.children[0];
      this.graphGroup.remove(child);
      this.disposeObjectTree(child);
    }

    this.nodeMeshes = [];
    this.liveEdges = [];

    for (const [index, edge] of this.layout.edges.entries()) {
      const line = buildLiveEdge(edge, index);
      this.liveEdges.push(line);
      this.graphGroup.add(line);
    }

    for (const node of this.layout.nodes) {
      const mesh = buildGalaxyNodeMesh(node);
      this.nodeMeshes.push(mesh);
      this.graphGroup.add(mesh);
    }
  }

  private disposeObjectTree(object: Group['children'][number]): void {
    object.traverse((child) => {
      if (child instanceof CSS2DObject) {
        child.element.remove();
      }
      if ('geometry' in child && child.geometry) {
        (child.geometry as { dispose?: () => void }).dispose?.();
      }
      if ('material' in child && child.material) {
        const material = child.material as { dispose?: () => void } | { dispose?: () => void }[];
        if (Array.isArray(material)) {
          material.forEach((entry) => entry.dispose?.());
        } else {
          material.dispose?.();
        }
      }
    });
  }

  private animate = (): void => {
    if (this.disposed) {
      return;
    }
    this.animationId = requestAnimationFrame(this.animate);
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      return;
    }
    this.clock += 0.016;

    if (this.controls) {
      this.controls.update();
    }

    for (const mesh of this.nodeMeshes) {
      const { node, originY } = mesh.userData;
      const targetY = originY + Math.sin(this.clock * 1.2 + mesh.position.x) * 0.04;
      mesh.position.y += (targetY - mesh.position.y) * 0.08;

      if (node.kind === 'core') {
        animateVaxonCoreOrb(
          mesh,
          this.clock,
          this.vaxonCoreMode,
          this.selectedNodeId === node.node_id,
          this.voiceEnergy,
        );
      } else if (node.kind === 'workspace') {
        const focusStrength =
          !this.selectedWorkspaceId || this.focusedNodeIds.has(node.node_id) ? 1 : 0.16;
        animateWorkspaceNode(
          mesh,
          this.clock,
          this.presenceAmp,
          this.selectedNodeId === node.node_id,
          focusStrength,
        );
      } else if (
        node.kind === 'run' &&
        this.agentStreamActive &&
        (!this.streamWorkspaceId || node.workspace_id === this.streamWorkspaceId)
      ) {
        const pulse = 1 + Math.sin(this.clock * 5.4 + mesh.position.x) * 0.11;
        mesh.scale.setScalar(pulse);
        const material = mesh.material as MeshStandardMaterial;
        material.emissiveIntensity = 1.55 + Math.sin(this.clock * 4.2) * 0.35;
      } else if (node.tone === 'attention' || node.tone === 'critical') {
        const pulse = 1 + Math.sin(this.clock * 3.2 + mesh.position.z) * 0.06;
        mesh.scale.setScalar(pulse);
      } else if (this.presenceAmp >= 0.9) {
        const pulse = 1 + Math.sin(this.clock * 2.8 + mesh.position.x) * 0.04;
        mesh.scale.setScalar(pulse);
      } else {
        mesh.scale.setScalar(1);
      }
    }

    this.liveEdges.forEach((edge) => animateLiveEdge(edge, this.clock, this.presenceAmp));
    if (this.specialtyFx && !animateSpecialtyDispatchFilament(this.specialtyFx, performance.now())) {
      this.clearSpecialtyDispatch();
    }
    if (this.scene) {
      animateGalaxyAmbience(this.scene, this.starfield, this.clock, this.presenceAmp);
    }

    if (this.graphGroup) {
      this.graphGroup.rotation.y += 0.0005 + this.presenceAmp * 0.0013;
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
      this.labelRenderer?.render(this.scene, this.camera);
    }
  };

  private handleResize = (): void => {
    if (!this.renderer || !this.camera || this.disposed) {
      return;
    }
    const width = this.container.clientWidth || 640;
    const height = this.container.clientHeight || 420;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.labelRenderer?.setSize(width, height);
  };

  private handlePointerMove = (event: PointerEvent): void => {
    if (!this.renderer) {
      return;
    }
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera!);
    const hits = this.raycaster.intersectObjects(this.nodeMeshes, false);
    this.renderer.domElement.style.cursor = hits.length > 0 ? 'pointer' : 'grab';
  };

  private handleClick = (event: MouseEvent): void => {
    if (!this.renderer || !this.camera) {
      return;
    }
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.nodeMeshes, false);
    const hit = hits[0]?.object as NodeMesh | undefined;
    if (hit?.userData?.node) {
      this.controls!.autoRotate = false;
      this.setSelectedNode(hit.userData.node.node_id);
      this.onNodeClick(hit.userData.node);
      return;
    }
    // Empty canvas click clears selection (Neo4j Bloom / Cognee pattern).
    if (this.selectedNodeId) {
      this.setSelectedNode(null);
      this.onClearSelection?.();
    }
  };
}
