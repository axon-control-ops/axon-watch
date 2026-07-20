import { describe, expect, it } from 'vitest';

import { resolveIdeLayoutShortcut } from './ide-layout-shortcuts';

describe('ide layout shortcuts', () => {
  const base = {
    layoutMode: 'ide',
    modKey: true,
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
});
