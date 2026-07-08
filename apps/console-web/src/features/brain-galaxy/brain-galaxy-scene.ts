import {
  AmbientLight,
  BufferAttribute,
  BufferGeometry,
  Color,
  Group,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  PointLight,
  Points,
  PointsMaterial,
  Raycaster,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

import type { BrainGraphNode, BrainGraphSnapshot } from '../../lib/operator-brain-graph-view';
import {
  GALAXY_BACKGROUND,
  GALAXY_STAR_COLOR,
  galaxyEdgeColor,
  galaxyNodeColors,
} from './brain-galaxy-colors';
import {
  layoutBrainGraph3D,
  type BrainGraphLayout3D,
  type PositionedBrainNode3D,
} from './layout-brain-graph-3d';
import { createPersonaMarkElement } from '../../lib/operator-persona-mark-view';

export type BrainGalaxyNodeClickHandler = (node: BrainGraphNode) => void;

type GalaxyNodeUserData = {
  node: BrainGraphNode;
  originY: number;
};

type NodeMesh = Mesh<SphereGeometry, MeshStandardMaterial> & {
  userData: GalaxyNodeUserData;
};

export class BrainGalaxyScene {
  private readonly container: HTMLElement;
  private readonly onNodeClick: BrainGalaxyNodeClickHandler;
  private renderer: WebGLRenderer | null = null;
  private scene: Scene | null = null;
  private camera: PerspectiveCamera | null = null;
  private controls: OrbitControls | null = null;
  private graphGroup: Group | null = null;
  private labelRenderer: CSS2DRenderer | null = null;
  private nodeMeshes: NodeMesh[] = [];
  private animationId = 0;
  private layout: BrainGraphLayout3D = { nodes: [], edges: [] };
  private clock = 0;
  private disposed = false;
  private readonly raycaster = new Raycaster();
  private readonly pointer = new Vector2();
  private resizeObserver: ResizeObserver | null = null;
  private selectedNodeId: string | null = null;
  private vaxonBusy = false;
  private readonly defaultCameraPosition = new Vector3(2.4, 3.8, 7.2);
  private readonly defaultTarget = new Vector3(0, 0, 0);

  constructor(container: HTMLElement, onNodeClick: BrainGalaxyNodeClickHandler) {
    this.container = container;
    this.onNodeClick = onNodeClick;
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
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(width, height, false);
    this.renderer.setClearColor(GALAXY_BACKGROUND, 1);
    this.container.appendChild(this.renderer.domElement);

    this.scene = new Scene();

    this.camera = new PerspectiveCamera(42, width / height, 0.1, 100);
    this.camera.position.copy(this.defaultCameraPosition);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.setSize(width, height);
    this.labelRenderer.domElement.style.position = 'absolute';
    this.labelRenderer.domElement.style.inset = '0';
    this.labelRenderer.domElement.style.pointerEvents = 'none';
    this.container.appendChild(this.labelRenderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 0.22;
    this.controls.minDistance = 3.2;
    this.controls.maxDistance = 12;
    this.controls.enablePan = false;

    const ambient = new AmbientLight(0x224466, 0.55);
    this.scene.add(ambient);

    const keyLight = new PointLight(0x48c4ff, 2.2, 20);
    keyLight.position.set(2, 4, 3);
    this.scene.add(keyLight);

    const rimLight = new PointLight(0xff8040, 0.8, 16);
    rimLight.position.set(-3, -1, -2);
    this.scene.add(rimLight);

    this.graphGroup = new Group();
    this.scene.add(this.graphGroup);
    this.scene.add(this.buildStarfield());

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
    this.camera.position.set(
      mesh.position.x + 0.6,
      mesh.position.y + 1.4,
      mesh.position.z + 2.8,
    );
    this.controls.update();
    this.setSelectedNode(nodeId);
  }

  setSelectedNode(nodeId: string | null): void {
    this.selectedNodeId = nodeId;
    this.applySelectionHighlight(nodeId);
  }

  setVaxonBusy(busy: boolean): void {
    this.vaxonBusy = busy;
  }

  private applySelectionHighlight(nodeId: string | null): void {
    for (const mesh of this.nodeMeshes) {
      const material = mesh.material as MeshStandardMaterial;
      const isSelected = Boolean(nodeId && mesh.userData.node.node_id === nodeId);
      const baseIntensity = galaxyNodeColors(mesh.userData.node).emissiveIntensity;
      material.emissiveIntensity = isSelected ? baseIntensity + 0.65 : baseIntensity;
      material.opacity = isSelected ? 1 : 1;
    }
  }

  dispose(): void {
    this.disposed = true;
    cancelAnimationFrame(this.animationId);

    if (this.renderer) {
      this.renderer.domElement.removeEventListener('click', this.handleClick);
      this.renderer.domElement.removeEventListener('pointermove', this.handlePointerMove);
    }

    this.resizeObserver?.disconnect();
    this.controls?.dispose();
    this.renderer?.dispose();

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
    this.nodeMeshes = [];
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

    for (const edge of this.layout.edges) {
      const geometry = new BufferGeometry().setFromPoints([
        new Vector3(edge.sourcePos.x, edge.sourcePos.y, edge.sourcePos.z),
        new Vector3(edge.targetPos.x, edge.targetPos.y, edge.targetPos.z),
      ]);
      const material = new LineBasicMaterial({
        color: galaxyEdgeColor(edge.kind),
        transparent: true,
        opacity: edge.kind === 'emits' ? 0.55 : 0.28,
      });
      const line = new Line(geometry, material);
      this.graphGroup.add(line);
    }

    for (const node of this.layout.nodes) {
      const mesh = this.buildNodeMesh(node);
      this.nodeMeshes.push(mesh);
      this.graphGroup.add(mesh);
    }
  }

  private buildNodeMesh(node: PositionedBrainNode3D): NodeMesh {
    const colors = galaxyNodeColors(node);
    const geometry = new SphereGeometry(node.radius, 24, 24);
    const material = new MeshStandardMaterial({
      color: colors.base,
      emissive: new Color(colors.emissive),
      emissiveIntensity: colors.emissiveIntensity,
      metalness: 0.35,
      roughness: 0.4,
    });
    const mesh = new Mesh(geometry, material);
    mesh.position.set(node.x, node.y, node.z);
    (mesh.userData as GalaxyNodeUserData) = { node, originY: node.y };

    if (node.kind === 'core') {
      const haloScale = 1.55;
      const halo = new Mesh(
        new SphereGeometry(node.radius * haloScale, 16, 16),
        new MeshStandardMaterial({
          color: colors.base,
          emissive: new Color(colors.emissive),
          emissiveIntensity: 0.55,
          transparent: true,
          opacity: 0.07,
          depthWrite: false,
        }),
      );
      mesh.add(halo);
    }

    if (node.kind === 'core' || node.kind === 'workspace') {
      const label = document.createElement('span');
      label.className = 'brain-galaxy-node-label';
      if (node.tone === 'attention') {
        label.classList.add('brain-galaxy-node-label--attention');
      }
      if (node.tone === 'critical') {
        label.classList.add('brain-galaxy-node-label--critical');
      }
      if (node.kind === 'core') {
        label.classList.add('brain-galaxy-node-label--core');
        label.appendChild(createPersonaMarkElement('xs'));
      } else {
        label.textContent = node.label;
      }
      const labelObject = new CSS2DObject(label);
      labelObject.position.set(0, node.radius + 0.18, 0);
      mesh.add(labelObject);
    }

    return mesh as NodeMesh;
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

  private buildStarfield(): Points {
    const count = 900;
    const positions = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const radius = 8 + Math.random() * 14;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[index * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[index * 3 + 2] = radius * Math.cos(phi);
    }
    const geometry = new BufferGeometry();
    geometry.setAttribute('position', new BufferAttribute(positions, 3));
    const material = new PointsMaterial({
      color: GALAXY_STAR_COLOR,
      size: 0.035,
      transparent: true,
      opacity: 0.65,
      sizeAttenuation: true,
    });
    return new Points(geometry, material);
  }

  private animate = (): void => {
    if (this.disposed) {
      return;
    }
    this.animationId = requestAnimationFrame(this.animate);
    this.clock += 0.016;

    if (this.controls) {
      this.controls.update();
    }

    for (const mesh of this.nodeMeshes) {
      const { node, originY } = mesh.userData;
      const targetY = originY + Math.sin(this.clock * 1.2 + mesh.position.x) * 0.04;
      mesh.position.y += (targetY - mesh.position.y) * 0.08;

      if (node.kind === 'core') {
        const busyBoost = this.vaxonBusy ? 0.06 : 0;
        const pulse = 1 + Math.sin(this.clock * (this.vaxonBusy ? 4.2 : 2.4)) * (0.08 + busyBoost);
        mesh.scale.setScalar(pulse);
      } else if (node.tone === 'attention' || node.tone === 'critical') {
        const pulse = 1 + Math.sin(this.clock * 3.2 + mesh.position.z) * 0.06;
        mesh.scale.setScalar(pulse);
      } else if (this.vaxonBusy) {
        const pulse = 1 + Math.sin(this.clock * 2.8 + mesh.position.x) * 0.04;
        mesh.scale.setScalar(pulse);
      } else {
        mesh.scale.setScalar(1);
      }

      const material = mesh.material as MeshStandardMaterial;
      if (node.kind === 'core') {
        const base = this.vaxonBusy ? 1.55 : 1.2;
        const swing = this.vaxonBusy ? 0.55 : 0.35;
        material.emissiveIntensity = base + Math.sin(this.clock * (this.vaxonBusy ? 4.2 : 2.4)) * swing;
      }
    }

    if (this.graphGroup) {
      this.graphGroup.rotation.y += this.vaxonBusy ? 0.0018 : 0.0005;
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
    }
  };
}
