import type { Ref } from 'vue';

import {
  type IdeActivityView,
  persistAgentDockCollapsed,
  persistIdeWorkbenchCollapsed,
  persistIdeExplorerCollapsed,
} from '../../../lib/ide-layout-prefs';

interface CreateIdeWorkbenchChromeSliceInput {
  ideTerminalRevealToken: Ref<number>;
  ideTerminalProblemsRevealToken: Ref<number>;
  ideTerminalToggleToken: Ref<number>;
  ideExplorerInlineCreateToken: Ref<number>;
  ideExplorerInlineCreateKind: Ref<'file' | 'folder'>;
  teamRosterRevealToken: Ref<number>;
  ideActivityView: Ref<IdeActivityView>;
  ideExplorerCollapsed: Ref<boolean>;
  ideWorkbenchCollapsed: Ref<boolean>;
  agentDockCollapsed: Ref<boolean>;
  ideAttentionPanelOpen: Ref<boolean>;
  ideBriefingPanelOpen: Ref<boolean>;
  ideVaxonDockPinned: Ref<boolean>;
}

export function createIdeWorkbenchChromeSlice(input: CreateIdeWorkbenchChromeSliceInput) {
  /** Bump reveal token only — CenterWorkbench persists visibility for the active layout mode. */
  function revealIdeTerminalPanel(): void {
    input.ideTerminalRevealToken.value += 1;
  }

  /** Reveal the terminal dock and switch WorkbenchTerminalDock to the Problems tab. */
  function revealIdeWorkbenchProblems(): void {
    input.ideTerminalRevealToken.value += 1;
    input.ideTerminalProblemsRevealToken.value += 1;
  }

  function toggleIdeTerminalPanel(): void {
    input.ideTerminalToggleToken.value += 1;
  }

  function focusIdeSidebarView(view: IdeActivityView): void {
    input.ideAttentionPanelOpen.value = false;
    input.ideBriefingPanelOpen.value = false;
    input.ideVaxonDockPinned.value = false;
    input.ideActivityView.value = view === 'agent' ? 'team' : view;
    input.ideExplorerCollapsed.value = false;
    persistIdeExplorerCollapsed(false);
  }

  function setIdeActivityView(view: IdeActivityView): void {
    if (view === 'agent') {
      focusIdeSidebarView('team');
      input.agentDockCollapsed.value = false;
      persistAgentDockCollapsed(false);
      return;
    }
    focusIdeSidebarView(view);
    if (view === 'terminal') {
      revealIdeTerminalPanel();
    }
  }

  function toggleIdeExplorer(): void {
    input.ideExplorerCollapsed.value = !input.ideExplorerCollapsed.value;
    persistIdeExplorerCollapsed(input.ideExplorerCollapsed.value);
    if (!input.ideExplorerCollapsed.value) {
      input.ideActivityView.value = 'explorer';
    }
  }

  function toggleIdeWorkbench(): void {
    input.ideWorkbenchCollapsed.value = !input.ideWorkbenchCollapsed.value;
    persistIdeWorkbenchCollapsed(input.ideWorkbenchCollapsed.value);
    if (input.ideWorkbenchCollapsed.value && input.agentDockCollapsed.value) {
      input.agentDockCollapsed.value = false;
      persistAgentDockCollapsed(false);
    }
  }

  function toggleAgentDock(): void {
    input.agentDockCollapsed.value = !input.agentDockCollapsed.value;
    persistAgentDockCollapsed(input.agentDockCollapsed.value);
  }

  /** Open Team sidebar and nudge roster chrome to scroll the active teammate into view. */
  function revealTeamRosterForActiveEmployee(): void {
    setIdeActivityView('team');
    input.teamRosterRevealToken.value += 1;
  }

  /** Focus Explorer and start inline file/folder creation in the tree. */
  function requestIdeExplorerInlineCreate(kind: 'file' | 'folder' = 'file'): void {
    input.ideExplorerInlineCreateKind.value = kind;
    focusIdeSidebarView('explorer');
    input.ideExplorerInlineCreateToken.value += 1;
  }

  return {
    revealIdeTerminalPanel,
    revealIdeWorkbenchProblems,
    toggleIdeTerminalPanel,
    focusIdeSidebarView,
    setIdeActivityView,
    toggleIdeExplorer,
    toggleIdeWorkbench,
    toggleAgentDock,
    revealTeamRosterForActiveEmployee,
    requestIdeExplorerInlineCreate,
  };
}
