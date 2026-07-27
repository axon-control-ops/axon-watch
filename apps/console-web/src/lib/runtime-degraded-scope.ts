/** Partition runtime degraded reasons into local stack vs remote public ingress. */

const REMOTE_INGRESS_MARKERS = [
  'public health',
  'host unreachable',
  'axon.edudashpro',
  'remote ingress',
  'tunnel stopped',
  'tunnel process',
  'cloudflare',
  'trycloudflare',
  'soft cutover',
] as const;

export function isRemoteIngressDegradedReason(reason: string): boolean {
  const text = reason.trim().toLowerCase();
  if (!text) {
    return false;
  }
  return REMOTE_INGRESS_MARKERS.some((marker) => text.includes(marker));
}

export function partitionDegradedReasons(reasons: string[] | null | undefined): {
  local: string[];
  remote: string[];
} {
  const local: string[] = [];
  const remote: string[] = [];
  for (const reason of reasons ?? []) {
    const trimmed = String(reason ?? '').trim();
    if (!trimmed) {
      continue;
    }
    if (isRemoteIngressDegradedReason(trimmed)) {
      remote.push(trimmed);
    } else {
      local.push(trimmed);
    }
  }
  return { local, remote };
}

export type RuntimeDegradedStateLike = {
  active: boolean;
  reasons: string[];
} | null | undefined;

/** True when degraded chrome should treat the local stack as unhealthy. */
export function localRuntimeDegradedActive(degraded: RuntimeDegradedStateLike): boolean {
  if (!degraded?.active) {
    return false;
  }
  return partitionDegradedReasons(degraded.reasons).local.length > 0;
}

/** True when the only degraded reasons are public-tunnel / remote ingress. */
export function remoteIngressAttentionActive(degraded: RuntimeDegradedStateLike): boolean {
  if (!degraded?.active) {
    return false;
  }
  const { local, remote } = partitionDegradedReasons(degraded.reasons);
  return local.length === 0 && remote.length > 0;
}

export function primaryRemoteIngressReason(degraded: RuntimeDegradedStateLike): string | null {
  if (!remoteIngressAttentionActive(degraded)) {
    return null;
  }
  return partitionDegradedReasons(degraded?.reasons).remote[0] ?? null;
}
