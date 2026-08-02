import { describe, expect, it } from 'vitest';

import { galaxyIntersectionIsVisible, shouldRenderGalaxy } from './galaxy-render-power';

describe('galaxy-render-power', () => {
  it('pauses when the document is hidden even if the container intersects', () => {
    expect(
      shouldRenderGalaxy({ documentHidden: true, containerVisible: true }),
    ).toBe(false);
  });

  it('pauses when the galaxy container is off-screen', () => {
    expect(
      shouldRenderGalaxy({ documentHidden: false, containerVisible: false }),
    ).toBe(false);
  });

  it('renders only when the tab and container are visible', () => {
    expect(
      shouldRenderGalaxy({ documentHidden: false, containerVisible: true }),
    ).toBe(true);
  });

  it('treats tiny intersections as not visible', () => {
    expect(galaxyIntersectionIsVisible(0)).toBe(false);
    expect(galaxyIntersectionIsVisible(0.01)).toBe(false);
    expect(galaxyIntersectionIsVisible(0.03)).toBe(true);
  });
});
