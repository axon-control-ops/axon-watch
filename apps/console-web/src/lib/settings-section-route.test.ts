import { describe, expect, it } from 'vitest';

import {
  normalizeSettingsSection,
  readSettingsSectionHash,
} from './settings-section-route';

describe('settings-section-route', () => {
  it('normalizes hash fragments to known settings sections', () => {
    expect(normalizeSettingsSection('#agents')).toBe('agents');
    expect(normalizeSettingsSection('runtime')).toBe('runtime');
    expect(normalizeSettingsSection('unknown')).toBeNull();
    expect(normalizeSettingsSection('')).toBeNull();
  });

  it('reads the active section from location hash', () => {
    expect(readSettingsSectionHash({ hash: '#email' })).toBe('email');
    expect(readSettingsSectionHash({ hash: '' })).toBeNull();
  });
});
