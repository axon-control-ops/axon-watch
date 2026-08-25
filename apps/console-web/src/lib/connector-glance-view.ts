import type { ConnectorProbeRecord } from '../api/control-plane';

export type ConnectorStatusBarChipId =
  | 'connector-glance'
  | 'connector-required-alert'
  | 'watch-offline';

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

/** Whether the optional connector glance chip would appear in the status bar. */
export function isLegacyConnectorGlanceVisible(input: ConnectorStatusBarChipInput): boolean {
  return buildConnectorGlanceChip(input) !== null;
}

export function isConnectorStatusBarChip(id: string): id is ConnectorStatusBarChipId {
  return (
    id === 'connector-glance' ||
    id === 'connector-required-alert' ||
    id === 'watch-offline'
  );
}

/** Warning status-bar chip when the watch lane is disconnected and probes are paused. */
export function buildWatchOfflineChip(watchConnected: boolean): ConnectorStatusBarChip | null {
  if (watchConnected) {
    return null;
  }

  return {
    id: 'watch-offline',
    label: 'WATCH OFFLINE',
    tone: 'warning',
  };
}

/** Single center status-bar chip for watch/connector health (offline beats stale counts). */
export function buildStatusBarConnectorChip(
  input: ConnectorStatusBarChipInput,
): ConnectorStatusBarChip | null {
  const watchOffline = buildWatchOfflineChip(input.watchConnected);
  if (watchOffline) {
    return watchOffline;
  }

  const requiredAlert = buildRequiredConnectorAlertChip(input);
  if (requiredAlert) {
    return requiredAlert;
  }

  return buildConnectorGlanceChip(input);
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
  const count = effectiveRequiredConnectorsUnavailable(
    input.summary,
    input.watchConnected,
  );
  if (count <= 0) {
    return null;
  }

  return {
    id: 'connector-required-alert',
    label: requiredConnectorAlertLabel(count),
    tone: 'warning',
  };
}

/** Low-severity status-bar chip reserved for optional connector notices. */
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

  return null;
}
