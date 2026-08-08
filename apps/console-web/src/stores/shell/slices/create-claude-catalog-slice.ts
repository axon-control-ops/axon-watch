import type { ComputedRef, Ref } from 'vue';

import {
  fetchClaudeRuntimeStatus,
  type ClaudeRuntimeStatusSnapshot,
} from '../../../api/control-plane';
import {
  resolveClaudeModel,
  type ClaudeCatalogRow,
} from '../../../lib/claude-catalog-view';
import {
  readComposerRuntimePrefs,
  writeComposerRuntimePrefs,
} from '../../../lib/composer-runtime-prefs';

type CatalogLoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface CreateClaudeCatalogSliceInput {
  claudeRuntimeStatus: Ref<ClaudeRuntimeStatusSnapshot | null>;
  claudeCatalogLoadState: Ref<CatalogLoadState>;
  claudeCatalogError: Ref<string | null>;
  claudeCatalogRows: ComputedRef<ClaudeCatalogRow[]>;
  composerRuntimePrefsRevision: Ref<number>;
  currentWorkspaceId: () => string | null;
}

export function createClaudeCatalogSlice(input: CreateClaudeCatalogSliceInput) {
  function migrateClaudeComposerModelIfNeeded(): void {
    const workspaceId = input.currentWorkspaceId();
    if (!workspaceId) {
      return;
    }
    const prefs = readComposerRuntimePrefs(workspaceId);
    const stored = prefs.claude_cli_model?.trim();
    if (!stored || stored === 'auto') {
      return;
    }
    const resolved = resolveClaudeModel(stored, input.claudeCatalogRows.value);
    if (resolved !== stored) {
      writeComposerRuntimePrefs(workspaceId, { claude_cli_model: resolved });
      input.composerRuntimePrefsRevision.value += 1;
    }
  }

  async function loadClaudeCatalog(forceRefresh = false): Promise<void> {
    input.claudeCatalogLoadState.value = 'loading';
    input.claudeCatalogError.value = null;

    try {
      const snapshot = await fetchClaudeRuntimeStatus({ forceRefresh });
      input.claudeRuntimeStatus.value = snapshot;
      input.claudeCatalogLoadState.value = 'loaded';
      migrateClaudeComposerModelIfNeeded();
    } catch (error) {
      input.claudeCatalogLoadState.value = 'error';
      input.claudeCatalogError.value =
        error instanceof Error ? error.message : 'claude catalog request failed';
    }
  }

  return {
    loadClaudeCatalog,
    migrateClaudeComposerModelIfNeeded,
  };
}
