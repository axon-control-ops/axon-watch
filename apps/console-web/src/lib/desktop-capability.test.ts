import { describe, expect, it } from 'vitest';

import { detectDesktopCapabilities, isDesktopRuntime } from './desktop-capability';

describe('detectDesktopCapabilities', () => {
  it('reports browser when Tauri is absent', () => {
    const flags = detectDesktopCapabilities({} as Window);
    expect(flags.runtime).toBe('browser');
    expect(flags.hostBridge).toBe(false);
    expect(isDesktopRuntime(flags)).toBe(false);
  });

  it('reports desktop when __AXON_DESKTOP__ is injected', () => {
    const flags = detectDesktopCapabilities({
      __AXON_DESKTOP__: {
        runtime: 'desktop',
        capabilities: {
          hostBridge: true,
          tray: true,
          notifications: true,
          openReveal: true,
          mediaControl: false,
          artifactIndex: true,
        },
      },
    } as Window);
    expect(flags.runtime).toBe('desktop');
    expect(flags.hostBridge).toBe(true);
    expect(flags.mediaControl).toBe(false);
    expect(isDesktopRuntime(flags)).toBe(true);
  });

  it('detects a Tauri 2 webview before the async Axon bootstrap arrives', () => {
    const flags = detectDesktopCapabilities({
      __TAURI_INTERNALS__: {},
    } as Window);
    expect(flags.runtime).toBe('desktop');
    expect(flags.hostBridge).toBe(false);
    expect(flags.notifications).toBe(false);
  });
});
