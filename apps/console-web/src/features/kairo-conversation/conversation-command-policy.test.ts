import { describe, expect, it } from 'vitest';

import { shouldAutoDispatchConverseCommand } from './conversation-command-policy';
import type { KairoConverseResponse } from '../../lib/kairo-converse-client';

function commandResponse(
  overrides: Partial<KairoConverseResponse> = {},
): KairoConverseResponse {
  return {
    turn_kind: 'command',
    reply: 'On it.',
    source: 'template',
    command_content: 'git status',
    requires_confirmation: false,
    action: null,
    artifacts: [],
    ...overrides,
  };
}

describe('shouldAutoDispatchConverseCommand', () => {
  it('auto-dispatches read-only commands when confirmation is not required', () => {
    expect(shouldAutoDispatchConverseCommand(commandResponse())).toBe(true);
  });

  it('waits for confirmation on execute-tier commands', () => {
    expect(
      shouldAutoDispatchConverseCommand(
        commandResponse({
          command_content: 'run npm run verify',
          requires_confirmation: true,
        }),
      ),
    ).toBe(false);
  });

  it('does not auto-dispatch non-command turns', () => {
    expect(
      shouldAutoDispatchConverseCommand(
        commandResponse({
          turn_kind: 'status_question',
          command_content: null,
          requires_confirmation: null,
        }),
      ),
    ).toBe(false);
  });
});
