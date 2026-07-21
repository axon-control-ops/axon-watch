import { describe, expect, it } from 'vitest';

import { resolveIdeLayoutShortcut } from './ide-layout-shortcuts';

describe('ide layout shortcuts', () => {
  const base = {
    layoutMode: 'ide',
    modKey: true,
    shiftKey: false,
    editableTarget: false,
  };

  it('ignores shortcuts outside shell modes or inside editable fields', () => {
    expect(
      resolveIdeLayoutShortcut({ ...base, layoutMode: 'landing', key: 'j' }),
    ).toBeNull();
    expect(
      resolveIdeLayoutShortcut({ ...base, editableTarget: true, key: 'j' }),
    ).toBeNull();
    expect(resolveIdeLayoutShortcut({ ...base, modKey: false, key: 'j' })).toBeNull();
  });

  it('maps terminal toggle in operator and IDE modes', () => {
    expect(resolveIdeLayoutShortcut({ ...base, layoutMode: 'operator', key: 'j' })).toBe(
      'toggle-terminal',
    );
    expect(resolveIdeLayoutShortcut({ ...base, key: 'J' })).toBe('toggle-terminal');
  });

  it('maps explorer and agent dock toggles in IDE mode only', () => {
    expect(resolveIdeLayoutShortcut({ ...base, key: 'b' })).toBe('toggle-explorer');
    expect(resolveIdeLayoutShortcut({ ...base, key: 'B' })).toBe('toggle-explorer');
    expect(resolveIdeLayoutShortcut({ ...base, key: '\\' })).toBe('toggle-agent-dock');
    expect(
      resolveIdeLayoutShortcut({ ...base, layoutMode: 'operator', key: 'b' }),
    ).toBeNull();
    expect(
      resolveIdeLayoutShortcut({ ...base, layoutMode: 'operator', key: '\\' }),
    ).toBeNull();
  });

  it('maps Source Control open in IDE mode with Ctrl/Cmd+Shift+G', () => {
    expect(
      resolveIdeLayoutShortcut({ ...base, shiftKey: true, key: 'g' }),
    ).toBe('open-source-control');
    expect(
      resolveIdeLayoutShortcut({ ...base, shiftKey: true, key: 'G' }),
    ).toBe('open-source-control');
    expect(
      resolveIdeLayoutShortcut({ ...base, layoutMode: 'operator', shiftKey: true, key: 'g' }),
    ).toBeNull();
    expect(resolveIdeLayoutShortcut({ ...base, key: 'g' })).toBeNull();
  });

  it('maps Search open in IDE mode with Ctrl/Cmd+Shift+F', () => {
    expect(
      resolveIdeLayoutShortcut({ ...base, shiftKey: true, key: 'f' }),
    ).toBe('open-search');
    expect(
      resolveIdeLayoutShortcut({ ...base, shiftKey: true, key: 'F' }),
    ).toBe('open-search');
    expect(
      resolveIdeLayoutShortcut({ ...base, layoutMode: 'operator', shiftKey: true, key: 'f' }),
    ).toBeNull();
    expect(resolveIdeLayoutShortcut({ ...base, key: 'f' })).toBeNull();
  });
});
