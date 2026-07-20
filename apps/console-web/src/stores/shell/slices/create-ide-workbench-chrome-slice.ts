import type { Ref } from 'vue';

import {
  type IdeActivityView,
  persistAgentDockCollapsed,
  persistIdeExplorerCollapsed,
} from '../../../lib/ide-layout-prefs';

interface CreateIdeWorkbenchChromeSliceInput {
  ideTerminalRevealToken: Ref<number>;
  ideTerminalToggleToken: Ref<number>;
  ideActivityView: Ref<IdeActivityView>;
  ideExplorerCollapsed: Ref<boolean>;
  agentDockCollapsed: Ref<boolean>;
  ideAttentionPanelOpen: Ref<boolean>;
  ideBriefingPanelOpen: Ref<boolean>;
}

export function createIdeWorkbenchChromeSlice(input: CreateIdeWorkbenchChromeSliceInput) {
  /** Bump reveal token only — CenterWorkbench persists visibility for the active layout mode. */
  function revealIdeTerminalPanel(): void {
    input.ideTerminalRevealToken.value += 1;
  }

  function toggleIdeTerminalPanel(): void {
    input.ideTerminalToggleToken.value += 1;
  }

  function focusIdeSidebarView(view: IdeActivityView): void {
    input.ideAttentionPanelOpen.value = false;
    input.ideBriefingPanelOpen.value = false;
    input.ideActivityView.value = view;
    input.ideExplorerCollapsed.value = false;
    persistIdeExplorerCollapsed(false);
  }

  function setIdeActivityView(view: IdeActivityView): void {
    focusIdeSidebarView(view);
    if (view === 'terminal') {
      revealIdeTerminalPanel();
      return;
    }
    if (view === 'agent') {
      input.agentDockCollapsed.value = false;
      persistAgentDockCollapsed(false);
    }
  }

  function toggleIdeExplorer(): void {
    input.ideExplorerCollapsed.value = !input.ideExplorerCollapsed.value;
    persistIdeExplorerCollapsed(input.ideExplorerCollapsed.value);
    if (!input.ideExplorerCollapsed.value) {
      input.ideActivityView.value = 'explorer';
    }
  }

  function toggleAgentDock(): void {
    input.agentDockCollapsed.value = !input.agentDockCollapsed.value;
    persistAgentDockCollapsed(input.agentDockCollapsed.value);
  }

  return {
    revealIdeTerminalPanel,
    toggleIdeTerminalPanel,
    focusIdeSidebarView,
    setIdeActivityView,
    toggleIdeExplorer,
    toggleAgentDock,
  };
}
