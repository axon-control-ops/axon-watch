import { describe, expect, it } from 'vitest';

import {
  formatDebugSessionLogEntry,
  shortDebugLocation,
} from './debug-session-log-view';

describe('debug-session-log-view', () => {
  it('formats refresh lookup as plain language without JSON', () => {
    const formatted = formatDebugSessionLogEntry({
      hypothesisId: 'H4',
      location: 'EnhancedBiometricAuth.restoreTargetUserSession',
      message: 'per-user refresh token lookup',
      data: {
        logLabel: 'authenticateWithBiometricForUser',
        targetUserId: 'd78e273f-d2d9-4000-a11c-225ea9cf7e22',
        hasRefresh: false,
        activeUserId: '136cf31c-b37c-45c0-9cf7-755bd1b9afbf',
      },
    });

    expect(formatted.hypothesisLabel).toBe('H4');
    expect(formatted.title).toBe('per-user refresh token lookup');
    expect(formatted.locationShort).toBe('restoreTargetUserSession');
    expect(formatted.details.join(' · ')).toContain('missing refresh token');
    expect(formatted.details.join(' · ')).toContain('target d78e273f');
    expect(formatted.details.join(' · ')).not.toContain('{');
    expect(formatted.details.join(' · ')).not.toContain('logLabel');
  });

  it('keeps failure reasons readable', () => {
    const formatted = formatDebugSessionLogEntry({
      hypothesisId: 'H5',
      location: 'ProfileSwitcher.handleSwitchAccount',
      message: 'switch result',
      data: {
        success: false,
        reason: 'target_refresh_missing',
        requiresPassword: true,
        error: 'No saved session found for this account.',
      },
    });

    expect(formatted.details).toEqual(
      expect.arrayContaining([
        'failed',
        'password required',
        'reason target_refresh_missing',
        'No saved session found for this account.',
      ]),
    );
  });

  it('shortens dotted locations to the method name', () => {
    expect(shortDebugLocation('EnhancedBiometricAuth.restoreTargetUserSession')).toBe(
      'restoreTargetUserSession',
    );
  });
});
