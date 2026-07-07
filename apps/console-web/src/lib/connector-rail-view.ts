import type { ConnectorProbeRecord } from '../api/control-plane';
import { LEGACY_AXON_LOCAL_FALLBACK_URL } from '../api/control-plane';

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
  tunnelStartAllowed: boolean;
}

export function connectorRailTone(status: string): ConnectorRailTone {
  if (status === 'ok') {
    return 'ok';
  }
  if (status === 'degraded') {
    return 'degraded';
  }
  if (status === 'unavailable') {
    return 'unavailable';
  }
  return 'unknown';
}

export function buildConnectorRailRows(items: ConnectorProbeRecord[]): ConnectorRailRow[] {
  return items.map((item) => {
    const connectorId = String(item.connector_id ?? '').trim();
    const isLegacy = connectorId === 'axon_local';
    const isTunnel = connectorId === 'cloudflare_tunnel';
    const tunnelMeta = item.tunnel;
    const tunnelUrl = String(tunnelMeta?.tunnel_url ?? '').trim() || null;
    const tunnelRunning = Boolean(tunnelMeta?.process_running);
    const tunnelStartAllowed = isTunnel && Boolean(tunnelMeta?.auth_ready) && !tunnelRunning;
    return {
      connectorId,
      label: String(item.display_name ?? connectorId),
      status: String(item.status ?? 'unknown'),
      tone: connectorRailTone(String(item.status ?? '')),
      required: Boolean(item.required),
      detail: String(item.detail ?? '').trim(),
      isLegacyFallback: isLegacy,
      fallbackUrl: isLegacy ? LEGACY_AXON_LOCAL_FALLBACK_URL : null,
      isTunnelConnector: isTunnel,
      tunnelUrl,
      tunnelRunning,
      tunnelStartAllowed,
    };
  });
}
