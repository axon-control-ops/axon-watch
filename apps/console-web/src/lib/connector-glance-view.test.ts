import { describe, expect, it } from 'vitest';

import {
  buildConnectorGlanceChip,
  buildRequiredConnectorAlertChip,
  buildStatusBarConnectorChip,
  buildWatchOfflineChip,
  effectiveRequiredConnectorsUnavailable,
  isConnectorStatusBarChip,
  isLegacyConnectorGlanceVisible,
} from './connector-glance-view';

const baseInput = {
  connectorsLoadState: 'loaded' as const,
  items: [] as const,
  summary: { required_unavailable: 0 },
  watchConnected: true,
  layoutMode: 'operator' as const,
};

describe('connector glance view', () => {
  it('identifies status-bar connector chips', () => {
    expect(isConnectorStatusBarChip('connector-glance')).toBe(true);
    expect(isConnectorStatusBarChip('connector-required-alert')).toBe(true);
    expect(isConnectorStatusBarChip('watch-offline')).toBe(true);
    expect(isConnectorStatusBarChip('phase')).toBe(false);
  });

  it('builds a watch-offline chip when the watch lane is disconnected', () => {
    expect(buildWatchOfflineChip(false)).toEqual({
      id: 'watch-offline',
      label: 'WATCH OFFLINE',
      tone: 'warning',
    });
    expect(buildWatchOfflineChip(true)).toBeNull();
  });

  it('builds a required connector alert when required probes are down', () => {
    const chip = buildRequiredConnectorAlertChip({
      ...baseInput,
      summary: { required_unavailable: 2 },
    });
    expect(chip).toEqual({
      id: 'connector-required-alert',
      label: '2 REQUIRED CONNECTORS DOWN',
      tone: 'warning',
    });
  });

  it('builds a legacy glance chip when optional Axon Local is offline', () => {
    const input = {
      ...baseInput,
      items: [
        {
          connector_id: 'axon_local',
          display_name: 'Legacy Axon Local',
          required: false,
          status: 'unavailable',
        },
      ],
    };
    expect(buildConnectorGlanceChip(input)?.label).toContain('OFFLINE');
    expect(isLegacyConnectorGlanceVisible(input)).toBe(true);
  });

  it('keeps required connector alert visible while connectors refresh', () => {
    const chip = buildRequiredConnectorAlertChip({
      ...baseInput,
      connectorsLoadState: 'loading',
      summary: { required_unavailable: 1 },
    });
    expect(chip?.label).toBe('1 REQUIRED CONNECTOR DOWN');
  });

  it('suppresses required-unavailable counts when watch is offline', () => {
    expect(
      effectiveRequiredConnectorsUnavailable({ required_unavailable: 2 }, false),
    ).toBe(0);
    expect(
      effectiveRequiredConnectorsUnavailable({ required_unavailable: 2 }, true),
    ).toBe(2);
  });

  it('prefers watch-offline over stale connector counts in the status bar', () => {
    expect(
      buildStatusBarConnectorChip({
        ...baseInput,
        watchConnected: false,
        summary: { required_unavailable: 2 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Legacy Axon Local',
            required: false,
            status: 'unavailable',
          },
        ],
      }),
    ).toEqual({
      id: 'watch-offline',
      label: 'WATCH OFFLINE',
      tone: 'warning',
    });
  });

  it('prefers required-down over legacy glance in the status bar', () => {
    expect(
      buildStatusBarConnectorChip({
        ...baseInput,
        summary: { required_unavailable: 1 },
        items: [
          {
            connector_id: 'axon_local',
            display_name: 'Legacy Axon Local',
            required: false,
            status: 'unavailable',
          },
        ],
      })?.id,
    ).toBe('connector-required-alert');
  });

  it('hides the legacy glance when required connectors are already alerting', () => {
    const input = {
      ...baseInput,
      summary: { required_unavailable: 1 },
      items: [
        {
          connector_id: 'axon_local',
          display_name: 'Legacy Axon Local',
          required: false,
          status: 'unavailable',
        },
      ],
    };
    expect(buildConnectorGlanceChip(input)).toBeNull();
    expect(isLegacyConnectorGlanceVisible(input)).toBe(false);
  });
});
