/**
 * Camera offset for overview + node focus.
 * Lower elevation + nearer orbit so the spherical shell reads as 3D
 * (the old high/far offset flattened the galaxy into a radar ring).
 */
export const GALAXY_FOCUS_CAMERA_OFFSET = {
  x: 4.6,
  y: 1.85,
  z: 5.4,
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
