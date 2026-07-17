import { describe, expect, it } from 'vitest';

import { buildConnectorGlanceChip, buildRequiredConnectorAlertChip, isLegacyConnectorGlanceVisible } from './connector-glance-view';

describe('buildRequiredConnectorAlertChip', () => {
  const base = {
    connectorsLoadState: 'loaded' as const,
    summary: { required_unavailable: 2 },
    watchConnected: true,
    layoutMode: 'operator' as const,
    items: [],
  };

  it('shows a warning chip when required connectors are down', () => {
    expect(buildRequiredConnectorAlertChip(base)).toEqual({
      id: 'connector-required-alert',
      label: '2 REQUIRED CONNECTORS DOWN',
      tone: 'warning',
    });
  });

  it('uses singular copy for one required connector', () => {
    expect(
      buildRequiredConnectorAlertChip({
        ...base,
        summary: { required_unavailable: 1 },
      })?.label,
    ).toBe('1 REQUIRED CONNECTOR DOWN');
  });

  it('hides the chip when required connectors are healthy', () => {
    expect(
      buildRequiredConnectorAlertChip({
        ...base,
        summary: { required_unavailable: 0 },
      }),
    ).toBeNull();
  });

  it('shows the chip in IDE mode when watch is connected', () => {
    expect(buildRequiredConnectorAlertChip({ ...base, layoutMode: 'ide' })).toEqual({
      id: 'connector-required-alert',
      label: '2 REQUIRED CONNECTORS DOWN',
      tone: 'warning',
    });
  });

  it('hides the chip when watch is offline', () => {
    expect(buildRequiredConnectorAlertChip({ ...base, watchConnected: false })).toBeNull();
  });
});

describe('buildConnectorGlanceChip', () => {
  const base = {
    connectorsLoadState: 'loaded' as const,
    summary: { required_unavailable: 0 },
    watchConnected: true,
    layoutMode: 'operator' as const,
    items: [
      {
        connector_id: 'axon_local',
        display_name: 'Axon Local',
        status: 'unavailable',
        required: false,
      },
    ],
  };

  it('shows a glance chip when optional legacy Axon Local is down and required connectors are ok', () => {
    expect(buildConnectorGlanceChip(base)).toEqual({
      id: 'connector-glance',
      label: 'LEGACY AXON LOCAL OFFLINE',
      tone: 'default',
    });
  });

  it('hides the chip when required connectors are down', () => {
    expect(
      buildConnectorGlanceChip({
        ...base,
        summary: { required_unavailable: 1 },
      }),
    ).toBeNull();
  });

  it('hides the chip when legacy Axon Local is healthy', () => {
    expect(
      buildConnectorGlanceChip({
        ...base,
        items: [{ ...base.items[0], status: 'ok' }],
      }),
    ).toBeNull();
  });

  it('shows the chip in IDE mode when watch is connected', () => {
    expect(buildConnectorGlanceChip({ ...base, layoutMode: 'ide' })).toEqual({
      id: 'connector-glance',
      label: 'LEGACY AXON LOCAL OFFLINE',
      tone: 'default',
    });
  });

  it('hides the chip when watch is offline', () => {
    expect(buildConnectorGlanceChip({ ...base, watchConnected: false })).toBeNull();
  });

  it('labels degraded legacy status distinctly', () => {
    expect(
      buildConnectorGlanceChip({
        ...base,
        items: [{ ...base.items[0], status: 'degraded' }],
      })?.label,
    ).toBe('LEGACY AXON LOCAL DEGRADED');
  });
});

describe('isLegacyConnectorGlanceVisible', () => {
  const base = {
    connectorsLoadState: 'loaded' as const,
    summary: { required_unavailable: 0 },
    watchConnected: true,
    layoutMode: 'ide' as const,
    items: [
      {
        connector_id: 'axon_local',
        display_name: 'Axon Local',
        status: 'unavailable',
        required: false,
      },
    ],
  };

  it('returns true when the legacy glance chip would render', () => {
    expect(isLegacyConnectorGlanceVisible(base)).toBe(true);
  });

  it('returns false when connectors are healthy', () => {
    expect(
      isLegacyConnectorGlanceVisible({
        ...base,
        items: [{ ...base.items[0], status: 'ok' }],
      }),
    ).toBe(false);
  });
});
