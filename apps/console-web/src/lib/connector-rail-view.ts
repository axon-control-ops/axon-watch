import type { ConnectorProbeRecord } from '../api/control-plane';
import { LEGACY_AXON_LOCAL_FALLBACK_URL } from '../api/connectors-api';

import { effectiveRequiredConnectorsUnavailable } from './connector-glance-view';

export type ConnectorRailSummary = {
  configured: number;
  ok: number;
  required_unavailable: number;
};

export type ConnectorRailTone = 'ok' | 'degraded' | 'unavailable' | 'unknown';

export interface ConnectorRailRow {
  connectorId: string;
  label: string;
  status: string;
  tone: ConnectorRailTone;
  required: boolean;
  detail: string;
  isLegacyFallback: boolean;
  fallbackUrl: string | null;
  isTunnelConnector: boolean;
  tunnelUrl: string | null;
  tunnelRunning: boolean;
  tunnelManaged: boolean;
  tunnelStartAllowed: boolean;
}

export function connectorRailTone(status: string): ConnectorRailTone {
  if (status === 'ok') {
    return 'ok';
  }
  if (status === 'degraded' || status === 'remote') {
    return 'degraded';
  }
  if (status === 'unavailable') {
    return 'unavailable';
  }
  return 'unknown';
}

/** Soften optional tunnel public-health failures so the rail does not look like local death. */
export function connectorRailDisplayStatus(item: {
  connector_id?: string | null;
  status?: string | null;
  tunnel?: {
    process_running?: boolean | null;
    public_health_ok?: boolean | null;
  } | null;
}): string {
  const status = String(item.status ?? 'unknown').trim() || 'unknown';
  const connectorId = String(item.connector_id ?? '').trim();
  if (connectorId !== 'cloudflare_tunnel') {
    return status;
  }
  if (status !== 'degraded') {
    return status;
  }
  const tunnel = item.tunnel;
  if (tunnel?.process_running && tunnel.public_health_ok === false) {
    return 'remote';
  }
  return status;
}

/** Prefer operator-readable remote-ingress copy for tunnel public-health failures. */
export function connectorRailDisplayDetail(item: {
  connector_id?: string | null;
  detail?: string | null;
  tunnel?: {
    process_running?: boolean | null;
    public_health_ok?: boolean | null;
    public_health_detail?: string | null;
  } | null;
}): string {
  const detail = String(item.detail ?? '').trim();
  const connectorId = String(item.connector_id ?? '').trim();
  if (connectorId !== 'cloudflare_tunnel') {
    return detail;
  }
  const tunnel = item.tunnel;
  if (tunnel?.process_running && tunnel.public_health_ok === false) {
    const publicDetail = String(tunnel.public_health_detail ?? '').trim();
    if (publicDetail) {
      return `remote ingress unhealthy (${publicDetail}); local Axon-X unaffected`;
    }
    if (detail.toLowerCase().includes('public health')) {
      return detail.includes('local Axon-X unaffected')
        ? detail
        : `${detail}; local Axon-X unaffected`;
    }
  }
  return detail;
}

/** Header summary for the Mission Control connectors rail. */
export function buildConnectorRailSummaryLabel(input: {
  loading: boolean;
  summary: ConnectorRailSummary | null;
  watchConnected: boolean;
}): string {
  if (input.loading) {
    return 'Loading…';
  }

  if (!input.watchConnected) {
    return 'Watch offline — probe counts paused';
  }

  const summary = input.summary;
  if (!summary) {
    return 'Connectors unavailable';
  }

  const requiredDown = effectiveRequiredConnectorsUnavailable(summary, true);
  return `${summary.ok}/${summary.configured} ok · ${requiredDown} required down`;
}

/** Body copy when watch probes are paused because the lane is disconnected. */
export function buildConnectorRailWatchOfflineStatus(watchConnected: boolean): string | null {
  if (watchConnected) {
    return null;
  }

  return 'Watch offline — connector probes paused until the watch reconnects.';
}

/** Error copy when watch commands must not run while the lane is disconnected. */
export function connectorMutationBlockedWhenWatchOffline(watchConnected: boolean): string | null {
  if (watchConnected) {
    return null;
  }

  return 'Watch offline — connector commands paused until the watch reconnects.';
}

/** Whether the connectors rail should show required-down emphasis styling. */
export function connectorRailNeedsEmphasis(input: {
  summary: ConnectorRailSummary | null;
  watchConnected: boolean;
}): boolean {
  return effectiveRequiredConnectorsUnavailable(input.summary, input.watchConnected) > 0;
}

export function buildConnectorRailRows(items: ConnectorProbeRecord[]): ConnectorRailRow[] {
  return items.map((item) => {
    const connectorId = String(item.connector_id ?? '').trim();
    const isLegacy = connectorId === 'axon_local';
    const isTunnel = connectorId === 'cloudflare_tunnel';
    const tunnelMeta = item.tunnel;
    const tunnelUrl = String(tunnelMeta?.tunnel_url ?? '').trim() || null;
    const tunnelRunning = Boolean(tunnelMeta?.process_running);
    const tunnelManaged = Boolean(tunnelMeta?.managed_process);
    const tunnelStartAllowed = isTunnel && Boolean(tunnelMeta?.auth_ready) && !tunnelRunning;
    const displayStatus = connectorRailDisplayStatus(item);
    return {
      connectorId,
      label: String(item.display_name ?? connectorId),
      status: displayStatus,
      tone: connectorRailTone(displayStatus),
      required: Boolean(item.required),
      detail: connectorRailDisplayDetail(item),
      isLegacyFallback: isLegacy,
      fallbackUrl: isLegacy ? LEGACY_AXON_LOCAL_FALLBACK_URL : null,
      isTunnelConnector: isTunnel,
      tunnelUrl,
      tunnelRunning,
      tunnelManaged,
      tunnelStartAllowed,
    };
  });
}
