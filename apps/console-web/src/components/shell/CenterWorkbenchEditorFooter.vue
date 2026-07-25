<script setup lang="ts">
import IdeEditorStatusBarPanels from './IdeEditorStatusBarPanels.vue';
import EditorStatusBarMeta from './EditorStatusBarMeta.vue';
import type {
  IdeEditorStatusAgentChip,
  IdeEditorStatusConnectorChip,
  IdeEditorStatusGitChip,
  IdeEditorStatusSearchChip,
  IdeEditorStatusTeamChip,
  IdeEditorStatusTerminalChip,
} from '../../lib/ide-editor-status-view';
import type { EditorAccessStatus } from '../../lib/editor-access-status-view';

defineProps<{
  isIdeMode: boolean;
  showMinimapToggle: boolean;
  editorMinimapEnabled: boolean;
  editorCursorLine: number;
  editorCursorColumn: number;
  editorLineCount: number;
  editorEol: 'CRLF' | 'LF';
  editorLanguageLabel: string;
  editorAccessStatus: EditorAccessStatus;
  terminalChip: IdeEditorStatusTerminalChip | null;
  connectorChip: IdeEditorStatusConnectorChip | null;
  gitChip: IdeEditorStatusGitChip | null;
  searchChip: IdeEditorStatusSearchChip | null;
  teamChip: IdeEditorStatusTeamChip | null;
  agentChip: IdeEditorStatusAgentChip | null;
}>();

const emit = defineEmits<{
  showTerminal: [];
  openConnectors: [];
  openSourceControl: [];
  openSearch: [];
  openTeam: [];
  showAgent: [];
  toggleMinimap: [];
}>();
</script>

<template>
  <div class="editor-statusbar editor-statusbar--mockup">
    <IdeEditorStatusBarPanels
      v-if="isIdeMode"
      :terminal-chip="terminalChip"
      :connector-chip="connectorChip"
      :git-chip="gitChip"
      :search-chip="searchChip"
      :team-chip="teamChip"
      :agent-chip="agentChip"
      @show-terminal="emit('showTerminal')"
      @open-connectors="emit('openConnectors')"
      @open-source-control="emit('openSourceControl')"
      @open-search="emit('openSearch')"
      @open-team="emit('openTeam')"
      @show-agent="emit('showAgent')"
    />
    <EditorStatusBarMeta
      :show-minimap-toggle="showMinimapToggle"
      :minimap-enabled="editorMinimapEnabled"
      :cursor-line="editorCursorLine"
      :cursor-column="editorCursorColumn"
      :line-count="editorLineCount"
      :eol="editorEol"
      :language-label="editorLanguageLabel"
      :access-status="editorAccessStatus"
      @toggle-minimap="emit('toggleMinimap')"
      @open-source-control="emit('openSourceControl')"
    />
  </div>
</template>
