import { computed, ref } from 'vue';

import {
  APP_SURFACE_EVENT,
  readAppSurface,
  type AppSurface,
} from '../lib/app-surface-route';

const surfaceVersion = ref(0);
let listenersBound = false;

function syncAppSurface(): void {
  surfaceVersion.value += 1;
}

function bindAppSurfaceListeners(): void {
  if (listenersBound || typeof window === 'undefined') {
    return;
  }
  window.addEventListener('popstate', syncAppSurface);
  window.addEventListener(APP_SURFACE_EVENT, syncAppSurface);
  listenersBound = true;
}

export function useAppSurface() {
  bindAppSurfaceListeners();

  const appSurface = computed<AppSurface>(() => {
    surfaceVersion.value;
    return readAppSurface();
  });

  return {
    appSurface,
    syncAppSurface,
  };
}
