<script setup lang="ts">
import type { ComposerMode } from '../../../composables/useAgentDockComposer';
import { MODE_OPTIONS } from '../../../composables/useAgentDockComposer';
import type { CursorCatalogRow } from '../../../lib/cursor-catalog-view';
import { agentExecutionAccessHint } from '../../../lib/agent-execution-access-prefs';
import {
  mcpToolDetail,
  type ComposerMcpTool,
} from '../../../lib/composer-mcp-tools-view';
import PersonaTitle from '../../PersonaTitle.vue';
import { useShellStore } from '../../../stores/shell';

type RuntimeTarget = {
  id: string;
  label: string;
  ready: boolean;
  available: boolean;
  auth: { message?: string };
};

type AttachmentChip = {
  key: string;
  label: string;
  kind: string;
};

defineProps<{
  showContextMenu: boolean;
  showToolsMenu: boolean;
  showModelMenu: boolean;
  showModeMenu: boolean;
  showAddModelsPanel: boolean;
  showRuntimeTargetsPanel: boolean;
  showAddModelsEntry: boolean;
  showExtraPinnedRows: boolean;
  showCursorCatalog: boolean;
  showVaultAction: boolean;
  attachmentChips: AttachmentChip[];
  mcpToolsForMode: ComposerMcpTool[];
  composerMode: ComposerMode;
  modeOptions: typeof MODE_OPTIONS;
  modeButtonLabel: string;
  activeMode: (typeof MODE_OPTIONS)[number];
  isFullAccessAgent: boolean;
  executionAccessHint: string;
  contextWorkspace: boolean;
  contextActiveFile: boolean;
  contextSelection: boolean;
  contextTerminal: boolean;
  contextIde: boolean;
  contextPinned: boolean;
  hasTerminalSnippet: boolean;
  selectionChipLabel: string;
  runtimeDetail: string;
  runtimeLabel: string;
  selectedRuntimeSummary: string;
  runtimeTargets: RuntimeTarget[];
  selectedModelId: string;
  selectedModelLabel: string;
  autoModelRow: CursorCatalogRow;
  autoToggleChecked: boolean;
  composerPickerRows: CursorCatalogRow[];
  extraPinnedRows: CursorCatalogRow[];
  cursorCatalogTotal: number;
  cursorCatalogStatus: string;
  cursorAuthLine: string;
  cursorStaleWarning: string;
  cursorManageRows: CursorCatalogRow[];
  cursorCatalogCount: string;
  modelSearchQuery: string;
  runtimeHint: string;
}>();

const emit = defineEmits<{
  'toggle-section': [section: 'context' | 'tools' | 'model' | 'mode'];
  'toggle-context': [kind: 'workspace' | 'file' | 'selection' | 'terminal' | 'ide' | 'pin'];
  'toggle-runtime-targets': [];
  'select-runtime-target': [runtimeId: string];
  'select-composer-model': [modelId: string];
  'select-manage-model': [modelId: string];
  'open-add-models': [];
  'close-add-models': [];
  'auto-toggle-click': [event: MouseEvent];
  'update:modelSearchQuery': [value: string];
  'select-mode': [mode: ComposerMode];
  'request-full-access': [];
  'switch-consultative': [];
  'open-vault': [];
}>();

const shell = useShellStore();

function runtimeStatusLine(record: RuntimeTarget): string {
  if (record.ready) return 'Ready';
  if (!record.available) return 'Not installed';
  return record.auth.message || 'Installed but not ready';
}
</script>

<template>
  <div class="agent-dock-composer__tools" @click.stop>
    <div class="agent-dock-composer__tool-group">
      <button
        type="button"
        class="agent-dock-composer__tool"
        :class="{ 'is-active': showContextMenu || attachmentChips.length > 0 }"
        title="Open context and quick run controls"
        aria-label="Open context menu"
        @click="emit('toggle-section', 'context')"
      >
        <span class="agent-dock-composer__tool-plus" aria-hidden="true">+</span>
        <span>Context</span>
        <span
          v-if="attachmentChips.length"
          class="agent-dock-composer__tool-count"
        >
          {{ attachmentChips.length }}
        </span>
      </button>
      <div
        v-if="showContextMenu"
        class="agent-dock-composer__menu agent-dock-composer__menu--context"
      >
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextWorkspace }"
          @click="emit('toggle-context', 'workspace')"
        >
          <span>Workspace</span>
          <small>{{ shell.currentWorkspace?.workspace_id ?? 'Unavailable' }}</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextActiveFile }"
          :disabled="!shell.activeWorkspaceFilePath"
          @click="emit('toggle-context', 'file')"
        >
          <span>Active file</span>
          <small>{{ shell.activeWorkspaceFilePath ?? 'Open a file first' }}</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextSelection }"
          :disabled="!shell.hasEditorSelection"
          @click="emit('toggle-context', 'selection')"
        >
          <span>Selection</span>
          <small>{{ shell.hasEditorSelection ? selectionChipLabel : 'Highlight code in the editor' }}</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextTerminal }"
          :disabled="!hasTerminalSnippet"
          @click="emit('toggle-context', 'terminal')"
        >
          <span>Terminal</span>
          <small>{{ hasTerminalSnippet ? 'Recent terminal output' : 'Run a command first' }}</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextIde }"
          @click="emit('toggle-context', 'ide')"
        >
          <span>IDE context</span>
          <small>Open file and editor state</small>
        </button>
        <button
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': contextPinned }"
          @click="emit('toggle-context', 'pin')"
        >
          <span>Pin context</span>
          <small>Keep current context across turns</small>
        </button>
      </div>
    </div>

    <div class="agent-dock-composer__tool-group">
      <button
        type="button"
        class="agent-dock-composer__tool"
        :class="{ 'is-active': showToolsMenu }"
        title="Runtime MCP tools available for this mode"
        aria-label="Open tools registry"
        @click="emit('toggle-section', 'tools')"
      >
        <span>Tools</span>
        <span
          v-if="mcpToolsForMode.length"
          class="agent-dock-composer__tool-count"
        >
          {{ mcpToolsForMode.length }}
        </span>
      </button>
      <div
        v-if="showToolsMenu"
        class="agent-dock-composer__menu agent-dock-composer__menu--tools"
      >
        <p class="agent-dock-composer__menu-heading">Runtime tools · {{ composerMode }}</p>
        <p
          v-if="shell.runtimeMcpToolsLoadState === 'loading'"
          class="agent-dock-composer__menu-note"
        >
          Loading tool registry…
        </p>
        <p
          v-else-if="!mcpToolsForMode.length"
          class="agent-dock-composer__menu-note"
        >
          No tools registered for this mode.
        </p>
        <button
          v-for="tool in mcpToolsForMode"
          :key="tool.id"
          type="button"
          class="agent-dock-composer__menu-item agent-dock-composer__menu-item--readonly"
          disabled
        >
          <span>{{ tool.label }}</span>
          <small>{{ mcpToolDetail(tool) }}</small>
        </button>
      </div>
    </div>

    <div class="agent-dock-composer__tool-group">
      <button
        type="button"
        class="agent-dock-composer__tool agent-dock-composer__tool--model"
        :class="{ 'is-active': showModelMenu }"
        :title="`Current runtime: ${runtimeDetail}`"
        :aria-label="`Open model picker: ${runtimeLabel}`"
        :aria-expanded="showModelMenu"
        @click="emit('toggle-section', 'model')"
      >
        <span class="agent-dock-composer__tool-icon" aria-hidden="true">⚡</span>
        <span class="agent-dock-composer__tool-label">{{ runtimeLabel }}</span>
        <span class="agent-dock-composer__tool-chevron" aria-hidden="true">▾</span>
      </button>
      <div v-if="showModelMenu" class="agent-dock-composer__menu agent-dock-composer__menu--runtime">
        <button
          type="button"
          class="agent-dock-composer__menu-section-toggle"
          :aria-expanded="showRuntimeTargetsPanel"
          @click.stop="emit('toggle-runtime-targets')"
        >
          <span class="agent-dock-composer__menu-section-label">Runtime target</span>
          <span class="agent-dock-composer__menu-section-value">{{ selectedRuntimeSummary }}</span>
          <span class="agent-dock-composer__menu-section-chevron" aria-hidden="true">
            {{ showRuntimeTargetsPanel ? '▴' : '▾' }}
          </span>
        </button>
        <div v-if="showRuntimeTargetsPanel" class="agent-dock-composer__menu-section-body">
          <button
            v-for="record in runtimeTargets"
            :key="record.id"
            type="button"
            class="agent-dock-composer__menu-item agent-dock-composer__menu-item--compact"
            :class="{ 'agent-dock-composer__menu-item--selected': record.id === shell.selectedRuntimeTargetId }"
            @click="emit('select-runtime-target', record.id)"
          >
            <span>{{ record.label }}</span>
            <small>{{ runtimeStatusLine(record) }}</small>
          </button>
        </div>

        <template v-if="showCursorCatalog">
          <p class="agent-dock-composer__menu-caption">Model catalog</p>
          <p class="agent-dock-composer__menu-note agent-dock-composer__menu-note--status">
            {{ cursorCatalogStatus }}
          </p>
          <p v-if="cursorAuthLine" class="agent-dock-composer__menu-note agent-dock-composer__menu-note--auth">
            {{ cursorAuthLine }}
          </p>
          <p v-if="shell.cursorCatalogLoadState === 'loading'" class="agent-dock-composer__menu-note">
            Loading Cursor models…
          </p>
          <p v-else-if="shell.cursorCatalogError" class="agent-dock-composer__menu-note">
            {{ shell.cursorCatalogError }}
          </p>

          <template v-if="!showAddModelsPanel">
            <label class="agent-dock-composer__auto-toggle" @click.stop>
              <span>
                <strong>Auto</strong>
                <small>{{ autoModelRow.description }}</small>
              </span>
              <input
                type="checkbox"
                role="switch"
                :checked="autoToggleChecked"
                @click="emit('auto-toggle-click', $event)"
              >
            </label>

            <button
              v-for="row in composerPickerRows"
              :key="row.id"
              type="button"
              class="agent-dock-composer__menu-item"
              :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
              :disabled="!row.available"
              @click="emit('select-composer-model', row.id)"
            >
              <span class="agent-dock-composer__model-label">
                {{ row.label }}
                <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
              </span>
              <small>{{ row.description }}</small>
            </button>

            <template v-if="showExtraPinnedRows">
              <p class="agent-dock-composer__menu-caption">Pinned models</p>
              <button
                v-for="row in extraPinnedRows"
                :key="row.id"
                type="button"
                class="agent-dock-composer__menu-item"
                :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
                :disabled="!row.available"
                @click="emit('select-composer-model', row.id)"
              >
                <span class="agent-dock-composer__model-label">
                  {{ row.label }}
                  <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
                </span>
                <small>{{ row.description }}</small>
              </button>
            </template>

            <button
              v-if="showAddModelsEntry"
              type="button"
              class="agent-dock-composer__menu-item agent-dock-composer__menu-item--add-models"
              @click.stop="emit('open-add-models')"
            >
              <span>Add models</span>
              <small>Browse {{ cursorCatalogTotal }} catalog models</small>
            </button>

            <p v-if="cursorStaleWarning" class="agent-dock-composer__menu-note agent-dock-composer__menu-note--warning">
              {{ cursorStaleWarning }}
            </p>
            <p v-if="shell.cursorRuntimeStatus?.catalog_source === 'fallback'" class="agent-dock-composer__menu-note">
              Live catalog unavailable — showing curated fallback models.
            </p>
          </template>

          <template v-else>
            <div class="agent-dock-composer__model-search-row">
              <button
                type="button"
                class="agent-dock-composer__menu-back"
                @click.stop="emit('close-add-models')"
              >
                ← Back
              </button>
              <input
                :value="modelSearchQuery"
                type="search"
                class="agent-dock-composer__model-search"
                placeholder="Search models"
                @input="emit('update:modelSearchQuery', ($event.target as HTMLInputElement).value)"
                @click.stop
              >
            </div>
            <p class="agent-dock-composer__menu-note">{{ cursorCatalogCount }}</p>
            <button
              v-for="row in cursorManageRows"
              :key="row.id"
              type="button"
              class="agent-dock-composer__menu-item agent-dock-composer__menu-item--compact"
              :class="{ 'agent-dock-composer__menu-item--selected': row.id === selectedModelId }"
              :disabled="!row.available"
              @click="emit('select-manage-model', row.id)"
            >
              <span class="agent-dock-composer__model-label">
                {{ row.label }}
                <span v-if="row.badge" class="agent-dock-composer__model-badge">{{ row.badge }}</span>
              </span>
              <small>{{ row.description }}</small>
            </button>
            <p
              v-if="!cursorManageRows.length"
              class="agent-dock-composer__menu-note"
            >
              No models match your search.
            </p>
          </template>
        </template>
        <p v-else class="agent-dock-composer__menu-note">
          Selected model: {{ selectedModelLabel }}
        </p>

        <p v-if="!showAddModelsPanel && runtimeHint && !cursorAuthLine" class="agent-dock-composer__menu-note">
          {{ runtimeHint }}
        </p>
        <p
          v-else-if="!showAddModelsPanel && runtimeHint && showVaultAction"
          class="agent-dock-composer__menu-note"
        >
          {{ runtimeHint }}
        </p>
        <button
          v-if="showVaultAction"
          type="button"
          class="agent-dock-composer__vault-action"
          @click="emit('open-vault')"
        >
          Open Vault
        </button>
      </div>
    </div>

    <div class="agent-dock-composer__tool-group">
      <button
        type="button"
        class="agent-dock-composer__tool agent-dock-composer__tool--mode"
        :class="{
          'is-active': showModeMenu,
          'agent-dock-composer__tool--mode-full-access': isFullAccessAgent,
        }"
        :data-mode="composerMode"
        :title="isFullAccessAgent ? executionAccessHint : activeMode.hint"
        :aria-label="`Conversation mode: ${modeButtonLabel}`"
        @click="emit('toggle-section', 'mode')"
      >
        <span class="agent-dock-composer__tool-icon" aria-hidden="true">{{ activeMode.icon }}</span>
        <span class="agent-dock-composer__tool-label agent-dock-composer__mode-chip">
          <PersonaTitle v-if="composerMode === 'kairo'" mark-size="xs" />
          <template v-else>{{ modeButtonLabel }}</template>
        </span>
        <span class="agent-dock-composer__tool-chevron" aria-hidden="true">▾</span>
      </button>
      <div v-if="showModeMenu" class="agent-dock-composer__menu">
        <p class="agent-dock-composer__menu-caption">Conversation mode</p>
        <button
          v-for="option in modeOptions"
          :key="option.key"
          type="button"
          class="agent-dock-composer__menu-item"
          :class="{ 'is-active': composerMode === option.key }"
          @click="emit('select-mode', option.key)"
        >
          <span class="agent-dock-composer__menu-item-label">
            <PersonaTitle v-if="option.key === 'kairo'" mark-size="xs" />
            <template v-else>{{ option.icon }} {{ option.label }}</template>
          </span>
          <small>{{ option.hint }}</small>
        </button>
        <template v-if="composerMode === 'agent'">
          <p class="agent-dock-composer__menu-caption">Execution access</p>
          <button
            type="button"
            class="agent-dock-composer__menu-item"
            :class="{ 'is-active': shell.agentExecutionAccess === 'consultative' }"
            @click="emit('switch-consultative')"
          >
            <span>◌ Consultative</span>
            <small>{{ agentExecutionAccessHint('consultative') }}</small>
          </button>
          <button
            type="button"
            class="agent-dock-composer__menu-item agent-dock-composer__menu-item--full-access"
            :class="{ 'is-active': shell.agentExecutionAccess === 'full' }"
            @click="emit('request-full-access')"
          >
            <span>⬡ Full Access</span>
            <small>{{ agentExecutionAccessHint('full') }}</small>
          </button>
        </template>
      </div>
    </div>
  </div>
</template>
