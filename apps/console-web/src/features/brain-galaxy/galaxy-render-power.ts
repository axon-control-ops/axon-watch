/** Decide when Brain Galaxy should keep its WebGL rAF loop alive. */

export function shouldRenderGalaxy(input: {
  documentHidden: boolean;
  containerVisible: boolean;
}): boolean {
  if (input.documentHidden) {
    return false;
  }
  return input.containerVisible;
}

export function galaxyIntersectionIsVisible(ratio: number): boolean {
  return ratio > 0.02;
}
