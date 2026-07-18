import { describe, expect, it } from 'vitest';

import {
  COMPOSER_TYPEAHEAD_LISTBOX_ID,
  composerTypeaheadActiveDescendant,
  composerTypeaheadOptionId,
} from './composer-typeahead-view';

describe('composer-typeahead-view', () => {
  it('builds stable listbox and option dom ids', () => {
    expect(COMPOSER_TYPEAHEAD_LISTBOX_ID).toBe('agent-dock-composer-typeahead');
    expect(composerTypeaheadOptionId(2)).toBe('agent-dock-composer-typeahead-opt-2');
  });

  it('returns active descendant only when the palette is open with rows', () => {
    expect(composerTypeaheadActiveDescendant(false, 3, 1)).toBeUndefined();
    expect(composerTypeaheadActiveDescendant(true, 0, 0)).toBeUndefined();
    expect(composerTypeaheadActiveDescendant(true, 4, 1)).toBe(
      'agent-dock-composer-typeahead-opt-1',
    );
    expect(composerTypeaheadActiveDescendant(true, 2, 9)).toBe(
      'agent-dock-composer-typeahead-opt-1',
    );
  });
});
