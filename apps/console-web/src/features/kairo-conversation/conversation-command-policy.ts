import type { KairoConverseResponse } from '../../lib/kairo-converse-client';

export function shouldAutoDispatchConverseCommand(response: KairoConverseResponse): boolean {
  if (response.turn_kind !== 'command' || !response.command_content) {
    return false;
  }
  return (
    response.requires_confirmation === false &&
    response.action_tier === 'reversible_auto'
  );
}
