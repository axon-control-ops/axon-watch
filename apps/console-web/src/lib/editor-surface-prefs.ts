export const EDITOR_MINIMAP_PREF_KEY = 'axon-x-editor-minimap-v1';

export function readEditorMinimapEnabled(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const stored = window.localStorage.getItem(EDITOR_MINIMAP_PREF_KEY);
  if (stored === 'false') {
    return false;
  }
  if (stored === 'true') {
    return true;
  }
  return true;
}

export function persistEditorMinimapEnabled(enabled: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(EDITOR_MINIMAP_PREF_KEY, enabled ? 'true' : 'false');
}
