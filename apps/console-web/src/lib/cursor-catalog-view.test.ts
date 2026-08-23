import { describe, expect, it } from 'vitest';

import {
  buildCursorCatalogRows,
  composerRuntimeFamilyLabel,
  cursorComposerPickerRows,
  cursorComposerPickerRowsForActiveModel,
  cursorComposerRuntimeLabel,
  cursorModelLabel,
  isCursorComposerModel,
  resolveCursorComposerModel,
} from './cursor-catalog-view';

describe('cursor-catalog-view', () => {
  const rows = buildCursorCatalogRows({
    installed: true,
    binary: '/usr/bin/cursor',
    auth: { logged_in: true, message: 'ok' },
    available_models: [
      { id: 'composer-2.5-fast', label: 'Composer 2.5 Fast', description: 'Composer 2.5 Fast (default)' },
      { id: 'composer-2.5', label: 'Composer 2.5', description: 'Composer 2.5' },
      { id: 'gpt-5.4-high', label: 'GPT-5.4 High', description: 'GPT-5.4 1M High' },
    ],
    cursor_models: [],
    catalog_source: 'live',
  });

  it('detects composer model ids', () => {
    expect(isCursorComposerModel('composer-2.5-fast')).toBe(true);
    expect(isCursorComposerModel('gpt-5.4-high')).toBe(false);
  });

  it('surfaces composer models first in the picker', () => {
    expect(cursorComposerPickerRows(rows).map((row) => row.id)).toEqual([
      'composer-2.5-fast',
      'composer-2.5',
    ]);
  });

  it('hides manual model rows while auto is enabled', () => {
    expect(
      cursorComposerPickerRowsForActiveModel({ rows, activeModelId: 'auto' }).map((row) => row.id),
    ).toEqual([]);
    expect(
      cursorComposerPickerRowsForActiveModel({
        rows,
        activeModelId: 'composer-2.5-fast',
      }).map((row) => row.id),
    ).toEqual(['composer-2.5-fast', 'composer-2.5']);
  });

  it('honors available catalog picks including non-composer models', () => {
    expect(resolveCursorComposerModel('gpt-5.4-high', rows)).toBe('gpt-5.4-high');
    expect(resolveCursorComposerModel('composer-2.5', rows)).toBe('composer-2.5');
    expect(resolveCursorComposerModel('auto', rows)).toBe('auto');
  });

  it('falls back stale or unavailable model pins to composer default', () => {
    expect(resolveCursorComposerModel('gpt-4-high', rows)).toBe('composer-2.5-fast');
    const withUnavailable = rows.map((row) =>
      row.id === 'gpt-5.4-high' ? { ...row, available: false } : row,
    );
    expect(resolveCursorComposerModel('gpt-5.4-high', withUnavailable)).toBe('composer-2.5-fast');
  });
});

describe('composer runtime display labels', () => {
  it('shows Cursor as the family strip label without local/cloud', () => {
    expect(composerRuntimeFamilyLabel('cursor')).toBe('Cursor');
    expect(composerRuntimeFamilyLabel('Cursor')).toBe('Cursor');
    expect(cursorModelLabel('auto', [])).toBe('Auto');
    expect(
      cursorModelLabel('cursor-grok-4.5-high-fast', [
        {
          id: 'cursor-grok-4.5-high-fast',
          label: 'Cursor Grok 4.5 Fast',
          description: '',
          available: true,
        },
      ]),
    ).toBe('Grok 4.5 Fast');
    expect(
      cursorComposerRuntimeLabel({
        family: 'cursor',
        scope: 'local',
        modelId: 'auto',
        rows: [],
      }),
    ).toBe('Cursor · Auto');
  });
});
