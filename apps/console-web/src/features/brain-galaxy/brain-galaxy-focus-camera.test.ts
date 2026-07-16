import { describe, expect, it } from 'vitest';

import {
  GALAXY_FOCUS_CAMERA_OFFSET,
  galaxyFocusCameraPosition,
} from './brain-galaxy-focus-camera';

describe('galaxyFocusCameraPosition', () => {
  it('keeps overview-scale distance from the focused node', () => {
    const camera = galaxyFocusCameraPosition({ x: 1, y: 2, z: 3 });
    expect(camera).toEqual({
      x: 1 + GALAXY_FOCUS_CAMERA_OFFSET.x,
      y: 2 + GALAXY_FOCUS_CAMERA_OFFSET.y,
      z: 3 + GALAXY_FOCUS_CAMERA_OFFSET.z,
    });
    const distance = Math.hypot(
      GALAXY_FOCUS_CAMERA_OFFSET.x,
      GALAXY_FOCUS_CAMERA_OFFSET.y,
      GALAXY_FOCUS_CAMERA_OFFSET.z,
    );
    // Old focus used ~3.2 units and filled the viewport; overview is ~8.5.
    expect(distance).toBeGreaterThan(7);
  });
});
