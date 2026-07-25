/**
 * Camera offset for overview + node focus.
 * Slightly farther than the tight shell so ~17 labeled workspaces read as
 * a constellation instead of a glowing clump.
 */
export const GALAXY_FOCUS_CAMERA_OFFSET = {
  x: 5.4,
  y: 2.35,
  z: 6.8,
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
