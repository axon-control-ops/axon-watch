import { MODE_OPTIONS, type ComposerMode } from './agent-dock/use-composer-menus';
import { useAgentDockComposerSetup } from './agent-dock/use-agent-dock-composer-setup';

export type { ComposerMode };
export { MODE_OPTIONS };

export function useAgentDockComposer() {
  return useAgentDockComposerSetup();
}
