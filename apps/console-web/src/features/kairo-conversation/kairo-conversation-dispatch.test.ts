import { beforeEach, describe, expect, it, vi } from 'vitest';

import { dispatchKairoConverseOutcome } from './kairo-conversation-dispatch';
import { setKairoLastRoutingReceipt, kairoLastRoutingReceipt } from './kairo-conversation-state';

describe('dispatchKairoConverseOutcome', () => {
  beforeEach(() => {
    setKairoLastRoutingReceipt(null);
  });

  it('awaits auto command dispatch and sets routing receipt', async () => {
    const order: string[] = [];
    const shell = {
      commandMutationState: 'idle',
      submitOperatorCommandContent: vi.fn(async () => {
        order.push('dispatch');
        await Promise.resolve();
        order.push('dispatch-done');
      }),
    };
    const execute = vi.fn(async () => {
      order.push('action');
    });

    const result = await dispatchKairoConverseOutcome(
      shell as never,
      {
        turn_kind: 'command',
        reply: 'ok',
        source: 'template',
        command_content: 'health',
        requires_confirmation: false,
        action_tier: 'reversible_auto',
        routing_receipt: 'lane=bounded_command',
        action: null,
        artifacts: [],
      },
      execute,
      'typed',
    );

    expect(result.commandDispatched).toBe(true);
    expect(shell.submitOperatorCommandContent).toHaveBeenCalledWith('health');
    expect(execute).not.toHaveBeenCalled();
    expect(order).toEqual(['dispatch', 'dispatch-done']);
    expect(kairoLastRoutingReceipt.value).toBe('lane=bounded_command');
  });

  it('awaits explicit converse action dispatch_command', async () => {
    const shell = {
      commandMutationState: 'idle',
      submitOperatorCommandContent: vi.fn(),
    };
    const execute = vi.fn(async () => undefined);

    const result = await dispatchKairoConverseOutcome(
      shell as never,
      {
        turn_kind: 'action',
        reply: 'dispatching',
        source: 'template',
        command_content: 'health',
        action: { type: 'dispatch_command', content: 'health' },
        artifacts: [],
        routing_receipt: 'lane=bounded_command',
      },
      execute,
      'voice',
    );

    expect(result.commandDispatched).toBe(true);
    expect(execute).toHaveBeenCalledOnce();
    expect(shell.submitOperatorCommandContent).not.toHaveBeenCalled();
  });

  it('records last action tier for autonomy UI', async () => {
    const { kairoLastActionTier, setKairoLastActionTier } = await import('./kairo-conversation-state');
    setKairoLastActionTier(null);
    const shell = {
      commandMutationState: 'idle',
      submitOperatorCommandContent: vi.fn(async () => undefined),
    };
    await dispatchKairoConverseOutcome(
      shell as never,
      {
        turn_kind: 'command',
        reply: 'ok',
        source: 'template',
        command_content: 'health',
        requires_confirmation: false,
        action_tier: 'reversible_auto',
        routing_receipt: 'lane=bounded_command',
        action: null,
        artifacts: [],
      },
      vi.fn(async () => undefined),
      'typed',
    );
    expect(kairoLastActionTier.value).toBe('reversible_auto');
  });
});
