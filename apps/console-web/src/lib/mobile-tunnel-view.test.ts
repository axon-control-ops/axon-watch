import { describe, expect, it } from 'vitest';

import { mobileTunnelActionState } from './mobile-tunnel-view';

describe('mobileTunnelActionState', () => {
  it('allows only start when no tunnel is running', () => {
    expect(
      mobileTunnelActionState({
        url: null,
        loading: false,
        mutationPending: false,
      }),
    ).toEqual({
      running: false,
      startDisabled: false,
      stopDisabled: true,
    });
  });

  it('allows only stop when the tunnel is running', () => {
    expect(
      mobileTunnelActionState({
        url: 'https://axon.example.test',
        loading: false,
        mutationPending: false,
      }),
    ).toEqual({
      running: true,
      startDisabled: true,
      stopDisabled: false,
    });
  });

  it('blocks both actions while status or a mutation is pending', () => {
    expect(
      mobileTunnelActionState({
        url: null,
        loading: true,
        mutationPending: false,
      }),
    ).toMatchObject({ startDisabled: true, stopDisabled: true });
    expect(
      mobileTunnelActionState({
        url: 'https://axon.example.test',
        loading: false,
        mutationPending: true,
      }),
    ).toMatchObject({ startDisabled: true, stopDisabled: true });
  });
});
