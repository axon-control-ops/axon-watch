import { describe, expect, it } from 'vitest';

import { addressFormForSpeaker } from './agent-streaming-ack';

describe('addressFormForSpeaker', () => {
  it('maps every console speaker to Sir King', () => {
    expect(addressFormForSpeaker('employee')).toBe('Sir King');
    expect(addressFormForSpeaker('vaxon')).toBe('Sir King');
    expect(addressFormForSpeaker('agent')).toBe('Sir King');
    expect(addressFormForSpeaker(null)).toBeNull();
  });
});
