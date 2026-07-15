import type { KairoConverseResponse } from '../../lib/kairo-converse-client';
import { useShellStore } from '../../stores/shell';
import { shouldAutoDispatchConverseCommand } from './conversation-command-policy';
import {
  setKairoLastActionTier,
  setKairoLastModelReceipt,
  setKairoLastRoutingReceipt,
} from './kairo-conversation-state';

type ShellStore = ReturnType<typeof useShellStore>;
type ConverseAction = NonNullable<KairoConverseResponse['action']>;

export async function dispatchKairoConverseOutcome(
  shell: ShellStore,
  response: KairoConverseResponse,
  executeConverseAction: (action: ConverseAction) => Promise<void>,
): Promise<{ commandDispatched: boolean }> {
  setKairoLastRoutingReceipt(response.routing_receipt ?? null);
  setKairoLastActionTier(response.action_tier ?? null);
  setKairoLastModelReceipt(response.model_receipt ?? null);

  if (response.action) {
    await executeConverseAction(response.action);
    return { commandDispatched: response.action.type === 'dispatch_command' };
  }
  if (shouldAutoDispatchConverseCommand(response)) {
    await shell.submitOperatorCommandContent(response.command_content!);
    return { commandDispatched: true };
  }
  return { commandDispatched: false };
}
