import type { ComputedRef, MaybeRef, Ref } from 'vue';
import { computed, toValue } from 'vue';

import { MODE_OPTIONS, type ComposerMode } from './use-composer-menus';
import type { AgentDockComposerAttachmentChip } from '../../components/ide/agent-dock/agent-dock-composer-toolbar-types';
import type { ComposerMcpTool } from '../../lib/composer-mcp-tools-view';
import type { CursorCatalogRow } from '../../lib/cursor-catalog-view';
import type { AgentDockComposerRuntimeTarget } from '../../components/ide/agent-dock/agent-dock-composer-toolbar-types';

type ModeOption = (typeof MODE_OPTIONS)[number];

type ToolbarPropsInput = {
  showContextMenu: MaybeRef<boolean>;
  showToolsMenu: MaybeRef<boolean>;
  showModelMenu: MaybeRef<boolean>;
  showModeMenu: MaybeRef<boolean>;
  showAddModelsPanel: MaybeRef<boolean>;
  showRuntimeTargetsPanel: MaybeRef<boolean>;
  showAddModelsEntry: MaybeRef<boolean>;
  showExtraPinnedRows: MaybeRef<boolean>;
  showCursorCatalog: MaybeRef<boolean>;
  showVaultAction: MaybeRef<boolean>;
  attachmentChips: MaybeRef<AgentDockComposerAttachmentChip[]>;
  composerImages: MaybeRef<unknown[]>;
  mcpToolsForMode: MaybeRef<ComposerMcpTool[]>;
  composerMode: MaybeRef<ComposerMode>;
  modeOptions: ModeOption[];
  modeButtonLabel: MaybeRef<string>;
  activeMode: MaybeRef<ModeOption>;
  isFullAccessAgent: MaybeRef<boolean>;
  executionAccessHint: MaybeRef<string>;
  sandboxSessionEnabled: MaybeRef<boolean>;
  sandboxEnvForced: MaybeRef<boolean>;
  sandboxHint: MaybeRef<string>;
  sandboxLabel: MaybeRef<string>;
  sandboxSessionPending: MaybeRef<boolean>;
  contextWorkspace: MaybeRef<boolean>;
  contextSelection: MaybeRef<boolean>;
  contextTerminal: MaybeRef<boolean>;
  contextIde: MaybeRef<boolean>;
  contextPinned: MaybeRef<boolean>;
  hasTerminalSnippet: MaybeRef<boolean>;
  selectionChipLabel: MaybeRef<string>;
  runtimeDetail: MaybeRef<string>;
  runtimeLabel: MaybeRef<string>;
  selectedRuntimeSummary: MaybeRef<string>;
  runtimeTargets: MaybeRef<AgentDockComposerRuntimeTarget[]>;
  selectedModelId: MaybeRef<string>;
  selectedModelLabel: MaybeRef<string>;
  autoModelRow: MaybeRef<CursorCatalogRow>;
  autoToggleChecked: MaybeRef<boolean>;
  composerPickerRows: MaybeRef<CursorCatalogRow[]>;
  extraPinnedRows: MaybeRef<CursorCatalogRow[]>;
  cursorCatalogTotal: MaybeRef<number>;
  cursorCatalogStatus: MaybeRef<string>;
  cursorAuthLine: MaybeRef<string>;
  cursorStaleWarning: MaybeRef<string | null>;
  cursorManageRows: MaybeRef<CursorCatalogRow[]>;
  cursorCatalogCount: MaybeRef<string>;
  modelSearchQuery: MaybeRef<string>;
  runtimeHint: MaybeRef<string>;
  canConvertInstructions: MaybeRef<boolean>;
};

export function useAgentDockComposerToolbarProps(
  input: ToolbarPropsInput,
) {
  return computed(() => ({
    showContextMenu: toValue(input.showContextMenu),
    showToolsMenu: toValue(input.showToolsMenu),
    showModelMenu: toValue(input.showModelMenu),
    showModeMenu: toValue(input.showModeMenu),
    showAddModelsPanel: toValue(input.showAddModelsPanel),
    showRuntimeTargetsPanel: toValue(input.showRuntimeTargetsPanel),
    showAddModelsEntry: toValue(input.showAddModelsEntry),
    showExtraPinnedRows: toValue(input.showExtraPinnedRows),
    showCursorCatalog: toValue(input.showCursorCatalog),
    showVaultAction: toValue(input.showVaultAction),
    attachmentChips: toValue(input.attachmentChips),
    composerImageCount: toValue(input.composerImages).length,
    mcpToolsForMode: toValue(input.mcpToolsForMode),
    composerMode: toValue(input.composerMode),
    modeOptions: input.modeOptions,
    modeButtonLabel: toValue(input.modeButtonLabel),
    activeMode: toValue(input.activeMode),
    isFullAccessAgent: toValue(input.isFullAccessAgent),
    executionAccessHint: toValue(input.executionAccessHint),
    sandboxSessionEnabled: toValue(input.sandboxSessionEnabled),
    sandboxEnvForced: toValue(input.sandboxEnvForced),
    sandboxHint: toValue(input.sandboxHint),
    sandboxLabel: toValue(input.sandboxLabel),
    sandboxSessionPending: toValue(input.sandboxSessionPending),
    contextWorkspace: toValue(input.contextWorkspace),
    contextSelection: toValue(input.contextSelection),
    contextTerminal: toValue(input.contextTerminal),
    contextIde: toValue(input.contextIde),
    contextPinned: toValue(input.contextPinned),
    hasTerminalSnippet: toValue(input.hasTerminalSnippet),
    selectionChipLabel: toValue(input.selectionChipLabel),
    runtimeDetail: toValue(input.runtimeDetail),
    runtimeLabel: toValue(input.runtimeLabel),
    selectedRuntimeSummary: toValue(input.selectedRuntimeSummary),
    runtimeTargets: toValue(input.runtimeTargets),
    selectedModelId: toValue(input.selectedModelId),
    selectedModelLabel: toValue(input.selectedModelLabel),
    autoModelRow: toValue(input.autoModelRow),
    autoToggleChecked: toValue(input.autoToggleChecked),
    composerPickerRows: toValue(input.composerPickerRows),
    extraPinnedRows: toValue(input.extraPinnedRows),
    cursorCatalogTotal: toValue(input.cursorCatalogTotal),
    cursorCatalogStatus: toValue(input.cursorCatalogStatus),
    cursorAuthLine: toValue(input.cursorAuthLine),
    cursorStaleWarning: toValue(input.cursorStaleWarning) ?? '',
    cursorManageRows: toValue(input.cursorManageRows),
    cursorCatalogCount: toValue(input.cursorCatalogCount),
    modelSearchQuery: toValue(input.modelSearchQuery),
    runtimeHint: toValue(input.runtimeHint),
    canConvertInstructions: toValue(input.canConvertInstructions),
  }));
}

export const PLAN_SOFT_SWITCH_REASON_LABEL: Record<string, string> = {
  planning_phrase: 'planning phrasing',
  bullet_heavy: 'structured list',
  long_multistep: 'long multi-step ask',
  plan_keyword: 'plan keyword',
};
