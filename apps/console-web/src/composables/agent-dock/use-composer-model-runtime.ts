import { computed, type Ref } from 'vue';

import {
  runtimeNeedsVaultAction,
  runtimeVaultHint,
} from '../../lib/agent-dock-runtime-view';
import { navigateToAppSurface } from '../../lib/app-surface-route';
import {
  cursorAutoModelDescription,
  cursorCatalogCountLabel,
  cursorCatalogModelRows,
  cursorCatalogStatusLabel,
  cursorComposerPickerRowsForActiveModel,
  cursorManageModelRows,
  cursorModelLabel,
  cursorPrimaryModelRows,
  cursorStaleModelWarning,
  isCursorAutoModel,
  isCursorComposerModel,
  type CursorCatalogRow,
  shouldShowCursorManualModelCatalog,
} from '../../lib/cursor-catalog-view';
import { CURSOR_PICKER_COMPOSER_IDS, CURSOR_PICKER_DEFAULT_MODEL } from '../../lib/cursor-picker-prefs';
import { composerCursorAuthLine } from '../../lib/runtime-auth-view';
import { codexModelLabel } from '../../lib/codex-catalog-view';
import { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

type UseComposerModelRuntimeOptions = {
  showAddModelsPanel: Ref<boolean>;
  showRuntimeTargetsPanel: Ref<boolean>;
  modelSearchQuery: Ref<string>;
  closeMenus: () => void;
};

export function useComposerModelRuntime(
  shell: ShellStore,
  options: UseComposerModelRuntimeOptions,
) {
  const { showAddModelsPanel, showRuntimeTargetsPanel, modelSearchQuery, closeMenus } = options;

  const runtimeTargets = computed(() => {
    const status = shell.runtimeStatus;
    if (!status) return [];
    return [...status.local, ...status.cloud];
  });
  const currentRuntimeTarget = computed(() => {
    const preferred = shell.selectedRuntimeTargetId;
    const status = shell.runtimeStatus;
    if (!status) return null;
    const records = [...status.local, ...status.cloud];
    if (preferred) {
      return records.find((record) => record.id === preferred) ?? records[0] ?? null;
    }
    const defaultRuntime = status.default_runtime;
    if (!defaultRuntime) return records[0] ?? null;
    return records.find((record) => record.id === defaultRuntime) ?? null;
  });
  const runtimeLabel = computed(() => {
    if (shell.composerRuntimeLabel) {
      return shell.composerRuntimeLabel;
    }
    const target = currentRuntimeTarget.value;
    if (target) {
      const scope = target.target_type === 'cloud' ? 'cloud' : 'local';
      return `${target.family} ${scope}`;
    }
    const identity = shell.runtimeSummary?.runtime_identity;
    if (!identity) return 'Runtime';
    return identity.model_name;
  });
  const runtimeDetail = computed(() => shell.composerRuntimeLabel || runtimeLabel.value);
  const showCursorCatalog = computed(() => {
    const target = currentRuntimeTarget.value;
    return (target?.family ?? 'cursor') === 'cursor';
  });
  const showCodexCatalog = computed(() => currentRuntimeTarget.value?.family === 'codex');
  const selectedModelId = computed(() => shell.selectedComposerModel || 'auto');
  const selectedModelLabel = computed(() =>
    showCodexCatalog.value
      ? codexModelLabel(selectedModelId.value, shell.codexCatalogRows)
      : cursorModelLabel(selectedModelId.value, shell.cursorCatalogRows),
  );
  const codexCatalogStatus = computed(() => {
    if (shell.codexCatalogLoadState === 'loading') return 'Loading Codex / ChatGPT models…';
    if (shell.codexCatalogError) return shell.codexCatalogError;
    if (shell.codexRuntimeStatus?.catalog_source === 'live') {
      return `${shell.codexCatalogRows.filter((row) => row.id !== 'auto').length} models available to your signed-in Codex account`;
    }
    return 'Codex model catalog is unavailable. Check the Codex CLI sign-in.';
  });
  const autoModelRow = computed(() =>
    shell.cursorCatalogRows.find((row) => row.id === 'auto') ?? {
      id: 'auto',
      label: 'Auto',
      description: cursorAutoModelDescription(shell.cursorCatalogRows),
      available: true,
    },
  );
  const composerPickerRows = computed(() => {
    const fromCatalog = cursorComposerPickerRowsForActiveModel({
      rows: shell.cursorCatalogRows,
      activeModelId: selectedModelId.value,
    });
    if (fromCatalog.length) {
      return fromCatalog;
    }
    if (!shouldShowCursorManualModelCatalog(selectedModelId.value)) {
      return [];
    }
    return CURSOR_PICKER_COMPOSER_IDS.map((id): CursorCatalogRow => ({
      id,
      label: id,
      description:
        id === CURSOR_PICKER_DEFAULT_MODEL
          ? 'Cursor Composer default — use when API quota models fail'
          : 'Cursor Composer model',
      available: true,
    }));
  });
  const extraPinnedRows = computed(() =>
    cursorPrimaryModelRows({
      rows: shell.cursorCatalogRows,
      activeModelId: selectedModelId.value,
      visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
    }).filter((row) => !isCursorComposerModel(row.id)),
  );
  const cursorManageRows = computed(() =>
    cursorManageModelRows({
      rows: shell.cursorCatalogRows,
      searchQuery: modelSearchQuery.value,
    }),
  );
  const cursorCatalogStatus = computed(() =>
    cursorCatalogStatusLabel({
      loading: shell.cursorCatalogLoadState === 'loading',
      snapshot: shell.cursorRuntimeStatus,
    }),
  );
  const cursorCatalogCount = computed(() =>
    cursorCatalogCountLabel({
      rows: shell.cursorCatalogRows,
      visibleExtraModelIds: shell.cursorPickerVisibleModelIds,
      searchQuery: modelSearchQuery.value,
    }),
  );
  const cursorStaleWarning = computed(() =>
    cursorStaleModelWarning({
      modelId: selectedModelId.value,
      rows: shell.cursorCatalogRows,
      snapshot: shell.cursorRuntimeStatus,
    }),
  );
  const cursorAuthLine = computed(() =>
    composerCursorAuthLine({
      target: currentRuntimeTarget.value,
      cursorSnapshot: shell.cursorRuntimeStatus,
    }),
  );
  const selectedRuntimeSummary = computed(() => {
    const target = currentRuntimeTarget.value;
    if (!target) {
      return 'No runtime selected';
    }
    const status = target.ready ? 'Ready' : runtimeStatusLine(target);
    return `${target.label} · ${status}`;
  });
  const autoModelEnabled = computed(() => isCursorAutoModel(selectedModelId.value));
  const showAddModelsEntry = computed(
    () => !showAddModelsPanel.value && shouldShowCursorManualModelCatalog(selectedModelId.value),
  );
  const autoToggleChecked = computed(() => autoModelEnabled.value && !showAddModelsPanel.value);
  const showExtraPinnedRows = computed(
    () => extraPinnedRows.value.length > 0 && !showAddModelsPanel.value,
  );
  const cursorCatalogTotal = computed(() => cursorCatalogModelRows(shell.cursorCatalogRows).length);
  const runtimeHint = computed(() => {
    if (shell.runtimeStatusError) {
      return shell.runtimeStatusError;
    }
    if (runtimeNeedsVaultAction(shell.runtimeStatus)) {
      return runtimeVaultHint(shell.runtimeStatus);
    }
    const target = currentRuntimeTarget.value;
    if (target?.ready) {
      return target.auth.message || 'Runtime is ready.';
    }
    if (target?.auth?.message) {
      return target.auth.message;
    }
    return 'Axon-X owns routing and falls back between configured runtimes.';
  });
  const showVaultAction = computed(() => runtimeNeedsVaultAction(shell.runtimeStatus));

  function openAddModelsPanel(): void {
    showAddModelsPanel.value = true;
  }

  function closeAddModelsPanel(): void {
    showAddModelsPanel.value = false;
    modelSearchQuery.value = '';
  }

  function selectRuntimeTarget(runtimeId: string): void {
    shell.setSelectedRuntimeTarget(runtimeId);
  }

  function selectComposerModel(modelId: string, options?: { keepMenuOpen?: boolean }): void {
    shell.setSelectedComposerModel(modelId);
    if (!options?.keepMenuOpen) {
      closeMenus();
    }
  }

  function toggleRuntimeTargetsPanel(): void {
    showRuntimeTargetsPanel.value = !showRuntimeTargetsPanel.value;
  }

  function onAutoToggleClick(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();
    if (autoModelEnabled.value && !showAddModelsPanel.value) {
      selectComposerModel(CURSOR_PICKER_DEFAULT_MODEL, { keepMenuOpen: true });
      return;
    }
    selectComposerModel('auto', { keepMenuOpen: true });
    closeAddModelsPanel();
  }

  function selectManageModelRow(modelId: string): void {
    selectComposerModel(modelId);
  }

  function openVaultSurface(): void {
    navigateToAppSurface('vault');
  }

  function runtimeStatusLine(record: (typeof runtimeTargets.value)[number]): string {
    if (record.ready) return 'Ready';
    if (!record.available) return 'Not installed';
    return record.auth.message || 'Installed but not ready';
  }

  return {
    autoModelRow,
    autoToggleChecked,
    closeAddModelsPanel,
    composerPickerRows,
    cursorAuthLine,
    cursorCatalogCount,
    cursorCatalogStatus,
    cursorCatalogTotal,
    codexCatalogRows: shell.codexCatalogRows,
    codexCatalogStatus,
    cursorManageRows,
    cursorStaleWarning,
    currentRuntimeTarget,
    extraPinnedRows,
    onAutoToggleClick,
    openAddModelsPanel,
    openVaultSurface,
    runtimeDetail,
    runtimeHint,
    runtimeLabel,
    runtimeStatusLine,
    runtimeTargets,
    selectComposerModel,
    selectManageModelRow,
    selectRuntimeTarget,
    selectedModelId,
    selectedModelLabel,
    selectedRuntimeSummary,
    showAddModelsEntry,
    showCursorCatalog,
    showCodexCatalog,
    showExtraPinnedRows,
    showVaultAction,
    toggleRuntimeTargetsPanel,
  };
}
