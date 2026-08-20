export const EDITOR_SURFACE_LAYOUT_EVENT = 'axon-editor-surface-layout';

/** Nudge Monaco hosts to re-measure after shell grid / workspace transitions. */
export function dispatchEditorSurfaceLayoutSync(): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(new CustomEvent(EDITOR_SURFACE_LAYOUT_EVENT));
}
