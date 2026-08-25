import { describe, expect, it } from 'vitest';

import {
  buildComposerModeAccessLabel,
  composerAccessBannerCopy,
  composerAccessMenuStatus,
  composerAccessTone,
  sandboxRootDirtyMessage,
  sandboxSessionHint,
  sandboxSessionLabel,
  sandboxStripDetailCopy,
  sandboxUnpromotedChangesMessage,
} from './sandbox-session-view';

describe('sandbox session view', () => {
  it('labels and hints reflect on/off and env force', () => {
    expect(sandboxSessionLabel(false)).toBe('Sandbox');
    expect(sandboxSessionLabel(true)).toBe('Sandbox · On');
    expect(sandboxSessionHint(false, false).toLowerCase()).toContain('enable');
    expect(sandboxSessionHint(true, false).toLowerCase()).toContain('on');
    expect(sandboxSessionHint(true, true).toLowerCase()).toContain('forced');
  });

  it('builds mode chip labels for access and sandbox', () => {
    expect(
      buildComposerModeAccessLabel({
        modeLabel: 'Agent',
        fullAccess: false,
        sandboxEnabled: false,
      }),
    ).toBe('Agent');
    expect(
      buildComposerModeAccessLabel({
        modeLabel: 'Agent',
        fullAccess: true,
        sandboxEnabled: false,
      }),
    ).toBe('Agent · Full');
    expect(
      buildComposerModeAccessLabel({
        modeLabel: 'Debug',
        fullAccess: true,
        sandboxEnabled: true,
      }),
    ).toBe('Debug · Sandbox · Full');
    expect(
      buildComposerModeAccessLabel({
        modeLabel: 'Ask',
        fullAccess: false,
        sandboxEnabled: true,
      }),
    ).toBe('Ask · Sandbox');
  });

  it('returns banner copy only for Sandbox states (Full Access uses mode-pill hover)', () => {
    expect(
      composerAccessBannerCopy({ fullAccess: false, sandboxEnabled: false }),
    ).toBeNull();
    expect(
      composerAccessBannerCopy({ fullAccess: true, sandboxEnabled: false }),
    ).toBeNull();
    expect(
      composerAccessBannerCopy({ fullAccess: false, sandboxEnabled: true }),
    ).toMatchObject({
      title: 'Sandbox',
      glyph: '▣',
      tone: 'sandbox',
    });
    expect(
      composerAccessBannerCopy({ fullAccess: true, sandboxEnabled: true }),
    ).toMatchObject({
      title: 'Sandbox · Full Access',
      glyph: '▣',
      tone: 'sandbox-full',
    });
  });

  it('maps access tone and menu status lines', () => {
    expect(composerAccessTone({ fullAccess: false, sandboxEnabled: false })).toBeNull();
    expect(composerAccessTone({ fullAccess: true, sandboxEnabled: false })).toBe('full');
    expect(composerAccessTone({ fullAccess: true, sandboxEnabled: true })).toBe('sandbox-full');
    expect(
      composerAccessMenuStatus({ fullAccess: true, sandboxEnabled: true }),
    ).toEqual({
      executionLine: 'Full Access active — routine tools autonomous; high-risk effects gated',
      sandboxLine: 'Sandbox on — disposable session copy',
      workerIsolationLine:
        'Full Auto supplies lazy isolated checkouts; manual workspace Sandbox remains enabled afterward',
    });
    expect(
      composerAccessMenuStatus({ fullAccess: true, sandboxEnabled: false }).workerIsolationLine,
    ).toContain('isolated checkouts');
  });

  it('builds strip and status warning copy for sandbox lifecycle', () => {
    expect(sandboxStripDetailCopy(false)).toContain('root preview');
    expect(sandboxStripDetailCopy(true)).toContain('Review and preview');
    expect(sandboxUnpromotedChangesMessage()).toContain('Review / Preview');
    expect(
      sandboxRootDirtyMessage({
        bound_branch: 'development',
        root_changed_paths: ['README.md', 'package.json'],
      }),
    ).toContain('development');
    expect(
      sandboxRootDirtyMessage({
        bound_branch: 'development',
        root_changed_paths: ['README.md', 'package.json'],
      }),
    ).toContain('README.md');
  });
});
