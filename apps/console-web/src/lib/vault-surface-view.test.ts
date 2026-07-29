import { describe, expect, it } from 'vitest';

import {
  appSurfacePath,
  normalizeAppPath,
  readAppSurface,
} from './app-surface-route';
import {
  formatVaultFullImportMessage,
  formatVaultTimestamp,
  looksLikeAxonVaultCsv,
  parseVaultImportCsv,
  parseVaultImportDraft,
  parseVaultImportExport,
  parseVaultImportJson,
  summarizeVaultImportKeys,
  vaultConsumerStatusLabel,
  vaultConsumerStatusTone,
  vaultImportFileLabel,
  vaultMissingKeysLabel,
  vaultReadyConsumerCount,
  vaultStateLabel,
} from './vault-surface-view';

describe('app surface route', () => {
  it('maps /vault to the vault surface', () => {
    expect(readAppSurface('/vault')).toBe('vault');
    expect(readAppSurface('/vault/')).toBe('vault');
    expect(readAppSurface('/')).toBe('console');
  });

  it('normalizes trailing slashes', () => {
    expect(normalizeAppPath('/vault/')).toBe('/vault');
    expect(appSurfacePath('vault')).toBe('/vault');
  });
});

describe('vault surface view helpers', () => {
  it('parses KEY=value import drafts', () => {
    expect(
      parseVaultImportDraft(`
# comment
SENTRY_AUTH_TOKEN=abc
POSTHOG_PERSONAL_API_KEY="xyz"
`),
    ).toEqual({
      SENTRY_AUTH_TOKEN: 'abc',
      POSTHOG_PERSONAL_API_KEY: 'xyz',
    });
  });

  it('parses CSV exports with header rows', () => {
    expect(
      parseVaultImportCsv(`name,value
SENTRY_AUTH_TOKEN,abc123
POSTHOG_PERSONAL_API_KEY,xyz789`),
    ).toEqual({
      SENTRY_AUTH_TOKEN: 'abc123',
      POSTHOG_PERSONAL_API_KEY: 'xyz789',
    });
  });

  it('parses JSON exports with secrets wrapper', () => {
    expect(
      parseVaultImportJson(
        JSON.stringify({
          secrets: {
            SENTRY_AUTH_TOKEN: 'abc123',
          },
        }),
      ),
    ).toEqual({
      SENTRY_AUTH_TOKEN: 'abc123',
    });
  });

  it('detects axon vault csv headers for full secret import', () => {
    expect(looksLikeAxonVaultCsv('name,category,username,password\nAnthropic,key,,sk-test')).toBe(true);
    expect(looksLikeAxonVaultCsv('name,value\nSENTRY_AUTH_TOKEN,abc')).toBe(false);
    expect(
      looksLikeAxonVaultCsv('folder,favorite,type,name,notes,login_username,login_password\nx,0,login,GH,,ops,secret'),
    ).toBe(true);
  });

  it('formats full vault import result summaries', () => {
    expect(
      formatVaultFullImportMessage(
        { added: 12, updated: 0, skipped: 3, source_secret_count: 15 },
        'vault-axon.csv',
      ),
    ).toBe('Imported vault-axon.csv (15 rows): 12 added, 0 updated, 3 skipped.');
  });

  it('detects csv/json by filename in parseVaultImportExport', () => {
    expect(
      parseVaultImportExport('name,value\nSENTRY_AUTH_TOKEN,abc', 'signal-export.csv'),
    ).toEqual({
      SENTRY_AUTH_TOKEN: 'abc',
    });
  });

  it('summarizes parsed import keys', () => {
    expect(
      summarizeVaultImportKeys({
        POSTHOG_PERSONAL_API_KEY: 'x',
        SENTRY_AUTH_TOKEN: 'y',
      }),
    ).toBe('2 key(s): POSTHOG_PERSONAL_API_KEY, SENTRY_AUTH_TOKEN');
  });

  it('maps consumer status to labels and tones', () => {
    expect(vaultConsumerStatusLabel('ready')).toBe('Ready');
    expect(vaultConsumerStatusTone('partial')).toBe('warning');
    expect(vaultConsumerStatusTone('missing')).toBe('critical');
  });

  it('summarizes vault inventory helpers', () => {
    expect(
      vaultReadyConsumerCount([
        {
          id: 'a',
          label: 'A',
          status: 'ready',
          required_keys: [],
          optional_keys: [],
          satisfied_keys: [],
          missing_keys: [],
          vault_surface: '/vault',
        },
        {
          id: 'b',
          label: 'B',
          status: 'missing',
          required_keys: [],
          optional_keys: [],
          satisfied_keys: [],
          missing_keys: ['X'],
          vault_surface: '/vault',
        },
      ]),
    ).toBe(1);
    expect(vaultImportFileLabel('/tmp/state/vault-import.json')).toBe('vault-import.json');
  });

  it('formats one-of missing key labels for runtime consumers', () => {
    expect(
      vaultMissingKeysLabel({
        id: 'codex_runtime',
        label: 'Codex CLI runtime',
        status: 'missing',
        required_keys: [],
        optional_keys: [],
        any_of_keys: ['CODEX_API_KEY', 'OPENAI_API_KEY'],
        satisfied_keys: [],
        missing_keys: ['one_of:CODEX_API_KEY|OPENAI_API_KEY'],
        vault_surface: '/vault',
      }),
    ).toBe('one of CODEX_API_KEY or OPENAI_API_KEY');
  });

  it('formats vault timestamps for display and handles invalid values', () => {
    expect(formatVaultTimestamp('2026-07-06T09:43:00Z', 'en-US')).toContain('2026');
    expect(formatVaultTimestamp('not-a-date', 'en-US')).toBe('Unknown');
  });

  it('does not treat a timed-out vault fetch as setup required', () => {
    expect(vaultStateLabel(null, { unavailable: true })).toBe('Status unavailable');
    expect(vaultStateLabel(null)).toBe('Setup required');
    expect(
      vaultStateLabel({
        is_setup: true,
        is_unlocked: true,
        import_file_present: false,
        import_file: '',
        available_keys: [],
        sources: [],
      }),
    ).toBe('Unlocked');
  });
});
