import { describe, expect, it } from 'vitest';

import {
  buildConnectorGlanceChip,
  buildRequiredConnectorAlertChip,
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
    expect(isConnectorStatusBarChip('phase')).toBe(false);
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
