import { describe, expect, it } from 'vitest';

import {
  addressFormForSpeaker,
  buildStreamingAckLine,
} from './agent-streaming-ack';

describe('buildStreamingAckLine', () => {
  it('builds a contextual receipts ack with Sir King', () => {
    expect(
      buildStreamingAckLine({
        operatorPrompt: "Walk me through receipts for Priya's last shift",
        address: 'Sir King',
      }),
    ).toBe('Pulling the shift receipts now, Sir King.');
  });

  it('falls back without inventing a fake On it reply', () => {
    expect(buildStreamingAckLine({ address: 'sir' })).toBe('Working that now, sir.');
    expect(buildStreamingAckLine({})).toBe('Working that now');
  });
});

describe('addressFormForSpeaker', () => {
  it('maps employee to Sir King and vaxon to sir', () => {
    expect(addressFormForSpeaker('employee')).toBe('Sir King');
    expect(addressFormForSpeaker('vaxon')).toBe('sir');
    expect(addressFormForSpeaker(null)).toBeNull();
  });
});
