export const COMPOSER_TYPEAHEAD_LISTBOX_ID = 'agent-dock-composer-typeahead';

export function composerTypeaheadOptionId(index: number): string {
  return `${COMPOSER_TYPEAHEAD_LISTBOX_ID}-opt-${index}`;
}

/** aria-activedescendant for the composer textarea when the palette is open. */
export function composerTypeaheadActiveDescendant(
  open: boolean,
  rowCount: number,
  selectedIndex: number,
): string | undefined {
  if (!open || rowCount <= 0) {
    return undefined;
  }
  const safe = Math.max(0, Math.min(selectedIndex, rowCount - 1));
  return composerTypeaheadOptionId(safe);
}
