import type { ConnectorProbeRecord } from '../api/control-plane';

export type ConnectorStatusBarChipId = 'connector-glance' | 'connector-required-alert';

export type ConnectorStatusBarChip = {
  id: ConnectorStatusBarChipId;
  label: string;
  tone: 'default' | 'warning';
};

/** @deprecated Use ConnectorStatusBarChip */
export type ConnectorGlanceChip = ConnectorStatusBarChip & { id: 'connector-glance'; tone: 'default' };

type ConnectorsSummary = {
  required_unavailable: number;
};

/** Required-unavailable counts are stale when watch is offline — suppress misleading UI. */
export function effectiveRequiredConnectorsUnavailable(
  summary: ConnectorsSummary | null,
  watchConnected: boolean,
): number {
  if (!watchConnected) {
    return 0;
  }
  return summary?.required_unavailable ?? 0;
}

export type ConnectorStatusBarChipInput = {
  connectorsLoadState: 'idle' | 'loading' | 'loaded' | 'error';
  items: readonly ConnectorProbeRecord[];
  summary: ConnectorsSummary | null;
  watchConnected: boolean;
  layoutMode: 'operator' | 'ide';
};

/** Whether the optional legacy Axon Local glance chip would appear in the status bar. */
export function isLegacyConnectorGlanceVisible(input: ConnectorStatusBarChipInput): boolean {
  return buildConnectorGlanceChip(input) !== null;
}

export function isConnectorStatusBarChip(id: string): id is ConnectorStatusBarChipId {
  return id === 'connector-glance' || id === 'connector-required-alert';
}

function requiredConnectorAlertLabel(count: number): string {
  if (count === 1) {
    return '1 REQUIRED CONNECTOR DOWN';
  }
  return `${count} REQUIRED CONNECTORS DOWN`;
}

/** Warning status-bar chip when one or more required watch connectors are unavailable. */
export function buildRequiredConnectorAlertChip(
  input: ConnectorStatusBarChipInput,
): ConnectorStatusBarChip | null {
  if (!input.watchConnected) {
    return null;
  }

  if (!input.summary) {
    return null;
  }

  const count = input.summary.required_unavailable;
  if (count <= 0) {
    return null;
  }

  return {
    id: 'connector-required-alert',
    label: requiredConnectorAlertLabel(count),
    tone: 'warning',
  };
}

const LEGACY_CONNECTOR_ID = 'axon_local';

function legacyConnectorLabel(status: string): string {
  const normalized = status.trim().toLowerCase();
  if (normalized === 'unavailable') {
    return 'LEGACY AXON LOCAL OFFLINE';
  }
  if (normalized === 'degraded') {
    return 'LEGACY AXON LOCAL DEGRADED';
  }
  return `LEGACY AXON LOCAL ${status.toUpperCase()}`;
}

/** Low-severity status-bar chip when optional legacy Axon Local is down but required connectors are ok. */
export function buildConnectorGlanceChip(
  input: ConnectorStatusBarChipInput,
): ConnectorGlanceChip | null {
  if (!input.watchConnected) {
    return null;
  }

  if (!input.summary) {
    return null;
  }

  if (input.summary.required_unavailable > 0) {
    return null;
  }

  const legacy = input.items.find(
    (item) => String(item.connector_id ?? '').trim() === LEGACY_CONNECTOR_ID,
  );
  if (!legacy || legacy.required) {
    return null;
  }

  const status = String(legacy.status ?? '').trim().toLowerCase();
  if (!status || status === 'ok') {
    return null;
  }

  return {
    id: 'connector-glance',
    label: legacyConnectorLabel(status),
    tone: 'default',
  };
}
