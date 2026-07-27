import { describe, expect, it } from 'vitest';

import {
  isRemoteIngressDegradedReason,
  localRuntimeDegradedActive,
  partitionDegradedReasons,
  primaryRemoteIngressReason,
  remoteIngressAttentionActive,
} from './runtime-degraded-scope';

describe('runtime-degraded-scope', () => {
  it('classifies public tunnel and remote ingress reasons', () => {
    expect(
      isRemoteIngressDegradedReason(
        'process up; public health failed (Name or service not known)',
      ),
    ).toBe(true);
    expect(
      isRemoteIngressDegradedReason(
        'remote ingress still points at http://localhost:7734; expected http://127.0.0.1:4173',
      ),
    ).toBe(true);
    expect(isRemoteIngressDegradedReason('watch summary stale')).toBe(false);
    expect(isRemoteIngressDegradedReason('HTTP 503')).toBe(false);
  });

  it('partitions mixed reasons', () => {
    expect(
      partitionDegradedReasons([
        'watch summary stale',
        'process up; public health failed (DNS)',
        'CLI auth missing',
      ]),
    ).toEqual({
      local: ['watch summary stale', 'CLI auth missing'],
      remote: ['process up; public health failed (DNS)'],
    });
  });

  it('treats remote-only degraded as ingress attention, not local outage', () => {
    const remoteOnly = {
      active: true,
      reasons: ['process up; public health failed (axon.edudashpro.org.za)'],
    };
    expect(localRuntimeDegradedActive(remoteOnly)).toBe(false);
    expect(remoteIngressAttentionActive(remoteOnly)).toBe(true);
    expect(primaryRemoteIngressReason(remoteOnly)).toContain('public health');

    const local = { active: true, reasons: ['watch summary stale'] };
    expect(localRuntimeDegradedActive(local)).toBe(true);
    expect(remoteIngressAttentionActive(local)).toBe(false);
  });
});
