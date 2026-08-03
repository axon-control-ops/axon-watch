import type { ComputedRef, Ref } from 'vue';

import {
  fetchCodexRuntimeStatus,
  type CodexRuntimeStatusSnapshot,
} from '../../../api/control-plane';
import type { CursorCatalogRow } from '../../../lib/cursor-catalog-view';

type CatalogLoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface CreateCodexCatalogSliceInput {
  codexRuntimeStatus: Ref<CodexRuntimeStatusSnapshot | null>;
  codexCatalogLoadState: Ref<CatalogLoadState>;
  codexCatalogError: Ref<string | null>;
  codexCatalogRows: ComputedRef<CursorCatalogRow[]>;
}

export function createCodexCatalogSlice(input: CreateCodexCatalogSliceInput) {
  async function loadCodexCatalog(forceRefresh = false): Promise<void> {
    input.codexCatalogLoadState.value = 'loading';
    input.codexCatalogError.value = null;
    try {
      input.codexRuntimeStatus.value = await fetchCodexRuntimeStatus({ forceRefresh });
      input.codexCatalogLoadState.value = 'loaded';
    } catch (error) {
      input.codexCatalogLoadState.value = 'error';
      input.codexCatalogError.value =
        error instanceof Error ? error.message : 'Codex model catalog request failed';
    }
  }

  return { loadCodexCatalog };
}
