export type AppSurface = 'console' | 'vault' | 'data' | 'mobile' | 'settings';

export function normalizeAppPath(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '');
  return trimmed || '/';
}

export function readAppSurface(pathname = window.location.pathname): AppSurface {
  const normalized = normalizeAppPath(pathname);
  if (normalized === '/vault') {
    return 'vault';
  }
  if (normalized === '/data') {
    return 'data';
  }
  if (normalized === '/mobile') {
    return 'mobile';
  }
  if (normalized === '/settings') {
    return 'settings';
  }
  return 'console';
}

export function appSurfacePath(surface: AppSurface): string {
  if (surface === 'vault') {
    return '/vault';
  }
  if (surface === 'data') {
    return '/data';
  }
  if (surface === 'mobile') {
    return '/mobile';
  }
  if (surface === 'settings') {
    return '/settings';
  }
  return '/';
}

export function navigateToAppSurface(surface: AppSurface): void {
  const nextPath = appSurfacePath(surface);
  if (normalizeAppPath(window.location.pathname) !== nextPath) {
    window.history.pushState({}, '', nextPath);
  }
  window.dispatchEvent(new Event('axon-app-surface'));
}

export const APP_SURFACE_EVENT = 'axon-app-surface';
