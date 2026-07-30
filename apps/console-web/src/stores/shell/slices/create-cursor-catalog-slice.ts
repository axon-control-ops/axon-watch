import type { ComputedRef, Ref } from 'vue';

import {
  fetchCursorRuntimeStatus,
  type CursorRuntimeStatusSnapshot,
} from '../../../api/control-plane';
import { saveWorkspaceComposerPrefs } from '../../../api/workspace-api';
import {
  resolveCursorComposerModel,
  type CursorCatalogRow,
} from '../../../lib/cursor-catalog-view';
import {
  readComposerRuntimePrefs,
  writeComposerRuntimePrefs,
} from '../../../lib/composer-runtime-prefs';

type CatalogLoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface CreateCursorCatalogSliceInput {
  cursorRuntimeStatus: Ref<CursorRuntimeStatusSnapshot | null>;
  cursorCatalogLoadState: Ref<CatalogLoadState>;
  cursorCatalogError: Ref<string | null>;
  cursorCatalogRows: ComputedRef<CursorCatalogRow[]>;
  composerRuntimePrefsRevision: Ref<number>;
  currentWorkspaceId: () => string | null;
}

export function createCursorCatalogSlice(input: CreateCursorCatalogSliceInput) {
  function syncWorkspaceComposerPrefsToServer(modelId: string): void {
    const workspaceId = input.currentWorkspaceId();
    if (!workspaceId) {
      return;
    }
    void saveWorkspaceComposerPrefs(workspaceId, {
      cursor_cli_model: modelId.trim() || 'auto',
    }).catch(() => undefined);
  }

  function migrateCursorComposerModelIfNeeded(): void {
    const workspaceId = input.currentWorkspaceId();
    if (!workspaceId) {
      return;
    }
    const prefs = readComposerRuntimePrefs(workspaceId);
    const stored = prefs.cursor_cli_model?.trim();
    if (!stored || stored === 'auto') {
      syncWorkspaceComposerPrefsToServer(stored || 'auto');
      return;
    }
    const resolved = resolveCursorComposerModel(stored, input.cursorCatalogRows.value);
    if (resolved !== stored) {
      writeComposerRuntimePrefs(workspaceId, { cursor_cli_model: resolved });
      input.composerRuntimePrefsRevision.value += 1;
    }
    syncWorkspaceComposerPrefsToServer(resolved);
  }

  async function loadCursorCatalog(forceRefresh = false): Promise<void> {
    input.cursorCatalogLoadState.value = 'loading';
    input.cursorCatalogError.value = null;

    try {
      const snapshot = await fetchCursorRuntimeStatus({ forceRefresh });
      input.cursorRuntimeStatus.value = snapshot;
      input.cursorCatalogLoadState.value = 'loaded';
      migrateCursorComposerModelIfNeeded();
    } catch (error) {
      input.cursorCatalogLoadState.value = 'error';
      input.cursorCatalogError.value =
        error instanceof Error ? error.message : 'cursor catalog request failed';
    }
  }

  return {
    loadCursorCatalog,
    migrateCursorComposerModelIfNeeded,
  };
}
