/** Open the IDE chat dock; optionally keep the current left activity panel. */

type IdeLayoutModeSetter = (mode: 'ide') => void;

export function openIdeComposerSurface(input: {
  layoutMode: string;
  setLayoutMode: IdeLayoutModeSetter;
  agentDockCollapsed: { value: boolean };
  persistAgentDockCollapsed: (collapsed: boolean) => void;
  ideActivityView: { value: string };
  commandFocusToken: { value: number };
  commandMutationError: { value: string | null };
  keepActivityView?: boolean;
}): void {
  input.commandMutationError.value = null;
  if (input.layoutMode !== 'ide') {
    input.setLayoutMode('ide');
  }
  input.agentDockCollapsed.value = false;
  input.persistAgentDockCollapsed(false);
  if (!input.keepActivityView && input.ideActivityView.value === 'agent') {
    input.ideActivityView.value = 'team';
  }
  input.commandFocusToken.value += 1;
}

export function openIdeComposerSurfaceWithDraft(
  input: {
    content: string;
    ideComposerDraft: { value: string };
    layoutMode: string;
    setLayoutMode: IdeLayoutModeSetter;
    agentDockCollapsed: { value: boolean };
    persistAgentDockCollapsed: (collapsed: boolean) => void;
    ideActivityView: { value: string };
    commandFocusToken: { value: number };
    commandMutationError: { value: string | null };
    keepActivityView?: boolean;
  },
): void {
  input.ideComposerDraft.value = input.content.trim();
  openIdeComposerSurface(input);
}
