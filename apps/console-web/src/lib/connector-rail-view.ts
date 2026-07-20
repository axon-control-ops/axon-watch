import type { ConnectorProbeRecord } from '../api/control-plane';
import { LEGACY_AXON_LOCAL_FALLBACK_URL } from '../api/connectors-api';

import { effectiveRequiredConnectorsUnavailable } from './connector-glance-view';

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
  if (status === 'degraded') {
    return 'degraded';
  }
  if (status === 'unavailable') {
    return 'unavailable';
  }
  return 'unknown';
}

type ConnectorsRailSummary = {
  configured: number;
  ok: number;
  required_unavailable: number;
};

/** Body copy when the watch lane is offline — suppresses stale probe rows. */
export function buildConnectorsRailWatchOfflineBody(): string {
  return 'Watch offline — connector probes paused until the watch reconnects. Use Refresh summary when the stack is back up.';
}

export function connectorsRailProbeListVisible(input: {
  loading: boolean;
  watchConnected: boolean;
  hasError: boolean;
}): boolean {
  return !input.loading && !input.hasError && input.watchConnected;
}

/** Header summary for Mission Control connectors rail — suppresses stale counts when watch is offline. */
export function buildConnectorsRailSummaryLabel(input: {
  loading: boolean;
  watchConnected: boolean;
  summary: ConnectorsRailSummary | null;
}): string {
  if (input.loading) {
    return 'Loading…';
  }

  if (!input.watchConnected) {
    return 'Watch offline';
  }

  const summary = input.summary;
  if (!summary) {
    return 'Connectors unavailable';
  }

  const requiredDown = effectiveRequiredConnectorsUnavailable(summary, true);
  return `${summary.ok}/${summary.configured} ok · ${requiredDown} required down`;
}

export function connectorsRailEmphasized(input: {
  watchConnected: boolean;
  summary: ConnectorsRailSummary | null;
}): boolean {
  return (
    effectiveRequiredConnectorsUnavailable(input.summary, input.watchConnected) > 0
  );
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
      tunnelManaged,
      tunnelStartAllowed,
    };
  });
}
