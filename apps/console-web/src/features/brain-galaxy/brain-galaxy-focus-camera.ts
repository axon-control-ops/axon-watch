/**
 * Camera offset used when focusing a galaxy node.
 * Matches the default overview orbit distance so workspace selection
 * frames the node without filling the viewport.
 */
export const GALAXY_FOCUS_CAMERA_OFFSET = {
  x: 2.4,
  y: 3.8,
  z: 7.2,
} as const;

export function galaxyFocusCameraPosition(node: {
  x: number;
  y: number;
  z: number;
}): { x: number; y: number; z: number } {
  return {
    x: node.x + GALAXY_FOCUS_CAMERA_OFFSET.x,
    y: node.y + GALAXY_FOCUS_CAMERA_OFFSET.y,
    z: node.z + GALAXY_FOCUS_CAMERA_OFFSET.z,
  };
}
