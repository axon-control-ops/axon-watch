import type { DesktopRuntime } from '../contracts/canonical';

export type DesktopCapabilityFlags = {
  runtime: DesktopRuntime;
  hostBridge: boolean;
  tray: boolean;
  notifications: boolean;
  openReveal: boolean;
  mediaControl: boolean;
  artifactIndex: boolean;
};

declare global {
  interface Window {
    __TAURI__?: unknown;
    __TAURI_INTERNALS__?: unknown;
    __AXON_DESKTOP__?: {
      runtime?: string;
      capabilities?: Partial<DesktopCapabilityFlags>;
      deviceId?: string;
    };
  }
}

/**
 * Browser builds always report runtime=browser with desktop flags false.
 * Tauri 2 injects window.__TAURI_INTERNALS__; older/global builds may expose
 * window.__TAURI__. The Rust bootstrap supplies the actual feature flags.
 */
export function detectDesktopCapabilities(
  win: Window | undefined = typeof window !== 'undefined' ? window : undefined,
): DesktopCapabilityFlags {
  const axon = win?.__AXON_DESKTOP__;
  const hasTauri = Boolean(
    win?.__TAURI_INTERNALS__ || win?.__TAURI__ || axon?.runtime === 'desktop',
  );
  if (!hasTauri) {
    return {
      runtime: 'browser',
      hostBridge: false,
      tray: false,
      notifications: false,
      openReveal: false,
      mediaControl: false,
      artifactIndex: false,
    };
  }
  const caps = axon?.capabilities ?? {};
  return {
    runtime: 'desktop',
    hostBridge: caps.hostBridge === true,
    tray: caps.tray === true,
    notifications: caps.notifications === true,
    openReveal: caps.openReveal === true,
    mediaControl: caps.mediaControl === true,
    artifactIndex: caps.artifactIndex === true,
  };
}

export function isDesktopRuntime(flags: DesktopCapabilityFlags = detectDesktopCapabilities()): boolean {
  return flags.runtime === 'desktop';
}
