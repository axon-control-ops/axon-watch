import { describe, expect, it } from 'vitest';

import { shouldAutoDispatchConverseCommand } from './conversation-command-policy';

describe('shouldAutoDispatchConverseCommand', () => {
  it('auto-dispatches only reversible allowlisted commands', () => {
    expect(
      shouldAutoDispatchConverseCommand({
        turn_kind: 'command',
        reply: 'ok',
        source: 'template',
        command_content: 'git status',
        requires_confirmation: false,
        action_tier: 'reversible_auto',
        action: null,
        artifacts: [],
      }),
    ).toBe(true);
  });

  it('blocks approval-gated commands', () => {
    expect(
      shouldAutoDispatchConverseCommand({
        turn_kind: 'command',
        reply: 'say yes',
        source: 'template',
        command_content: 'run npm run verify',
        requires_confirmation: true,
        action_tier: 'approval_gated',
        action: null,
        artifacts: [],
      }),
    ).toBe(false);
  });

  it('blocks inconsistent backend responses even when confirmation is false', () => {
    expect(
      shouldAutoDispatchConverseCommand({
        turn_kind: 'command',
        reply: 'unsafe mismatch',
        source: 'template',
        command_content: 'run npm run verify',
        requires_confirmation: false,
        action_tier: 'approval_gated',
        action: null,
        artifacts: [],
      }),
    ).toBe(false);

    expect(
      shouldAutoDispatchConverseCommand({
        turn_kind: 'command',
        reply: 'missing policy receipt',
        source: 'template',
        command_content: 'health',
        requires_confirmation: false,
        action: null,
        artifacts: [],
      }),
    ).toBe(false);
  });
});
