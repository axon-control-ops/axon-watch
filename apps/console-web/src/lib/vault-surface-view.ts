export type VaultConsumerStatus = 'ready' | 'partial' | 'missing';

export interface VaultSubscriptionAuth {
  installed?: boolean;
  logged_in?: boolean;
  account_label?: string;
  message?: string;
}

export interface VaultConsumerRecord {
  id: string;
  label: string;
  status: VaultConsumerStatus;
  required_keys: string[];
  optional_keys: string[];
  any_of_keys?: string[];
  satisfied_keys: string[];
  missing_keys: string[];
  auth_note?: string;
  subscription_auth?: VaultSubscriptionAuth | null;
  vault_surface: string;
}

export interface VaultStatusSnapshot {
  is_setup?: boolean;
  is_unlocked?: boolean;
  ttl_remaining?: number;
  auto_unlock_enabled?: boolean;
  import_file_present: boolean;
  import_file: string;
  imported_keys?: string[];
  imported_key_count?: number;
  available_keys: string[];
  sources: string[];
  consumers?: VaultConsumerRecord[];
  known_keys?: string[];
  import_hint?: string;
}

export interface VaultSentryValidation {
  ok: boolean;
  present: boolean;
  read_ok: boolean;
  write_ok: boolean;
  project_found: boolean;
  checked_at: string;
  token_key?: string;
  org_key?: string;
  project_key?: string;
  org_slug?: string;
  project_slug?: string;
  token_prefix?: string;
  token_length?: number;
  status_code?: number | null;
  visible_project_count?: number;
  detail?: string;
  write_detail?: string;
}

export interface VaultSecretRecord {
  id: number;
  name: string;
  category: string;
  username: string;
  url: string;
  notes_preview: string;
  created_at: string;
  updated_at: string;
}

export interface VaultSecretDetail extends VaultSecretRecord {
  password: string;
  notes: string;
}

export function vaultStateLabel(
  snapshot: VaultStatusSnapshot | null,
  options?: { unavailable?: boolean },
): string {
  if (options?.unavailable && !snapshot) {
    return 'Status unavailable';
  }
  if (!snapshot?.is_setup) {
    return 'Setup required';
  }
  if (!snapshot.is_unlocked) {
    return 'Locked';
  }
  return 'Unlocked';
}

export function vaultTtlLabel(seconds: number | undefined): string {
  const value = Number(seconds ?? 0);
  if (value <= 0) {
    return 'Expired';
  }
  if (value >= 3600) {
    return `${Math.round(value / 3600)}h remaining`;
  }
  return `${Math.max(1, Math.round(value / 60))}m remaining`;
}

export function vaultConsumerStatusLabel(status: VaultConsumerStatus): string {
  switch (status) {
    case 'ready':
      return 'Ready';
    case 'partial':
      return 'Partial';
    default:
      return 'Missing credentials';
  }
}

export function vaultConsumerStatusTone(status: VaultConsumerStatus): string {
  switch (status) {
    case 'ready':
      return 'ok';
    case 'partial':
      return 'warning';
    default:
      return 'critical';
  }
}

export function vaultReadyConsumerCount(consumers: VaultConsumerRecord[]): number {
  return consumers.filter((consumer) => consumer.status === 'ready').length;
}

export function vaultMissingKeysLabel(consumer: VaultConsumerRecord): string {
  const labels = consumer.missing_keys.map((item) => {
    if (item === 'subscription_or_api_key') {
      return 'CLI login or optional API key';
    }
    if (!item.startsWith('one_of:')) {
      return item;
    }
    const options = item
      .slice('one_of:'.length)
      .split('|')
      .map((value) => value.trim())
      .filter(Boolean);
    return options.length ? `one of ${options.join(' or ')}` : item;
  });
  return labels.join(', ');
}

export function vaultImportFileLabel(importFile: string): string {
  const trimmed = importFile.trim();
  if (!trimmed) {
    return 'Not configured';
  }
  const parts = trimmed.split(/[/\\]/);
  return parts[parts.length - 1] ?? trimmed;
}

export function formatVaultTimestamp(timestamp: string, locale?: string): string {
  const value = Date.parse(timestamp);
  if (Number.isNaN(value)) {
    return 'Unknown';
  }
  return new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

export function parseVaultImportDraft(raw: string): Record<string, string> {
  const secrets: Record<string, string> = {};
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) {
      continue;
    }
    const [key, ...rest] = trimmed.split('=');
    const name = key.trim();
    const value = rest.join('=').trim().replace(/^['"]|['"]$/g, '');
    if (name && value) {
      secrets[name] = value;
    }
  }
  return secrets;
}

const CSV_KEY_HEADERS = new Set(['key', 'name', 'variable', 'env', 'env_key', 'secret_name']);
const CSV_VALUE_HEADERS = new Set(['value', 'secret', 'env_value', 'token', 'credential']);

function splitCsvRow(line: string): string[] {
  const cells: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (inQuotes && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (char === ',' && !inQuotes) {
      cells.push(current.trim());
      current = '';
      continue;
    }
    current += char;
  }

  cells.push(current.trim());
  return cells.map((cell) => cell.replace(/^['"]|['"]$/g, ''));
}

export function parseVaultImportCsv(raw: string): Record<string, string> {
  const lines = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));

  if (!lines.length) {
    return {};
  }

  const secrets: Record<string, string> = {};
  const firstCells = splitCsvRow(lines[0] ?? '');
  const headerLooksLikeLabels =
    firstCells.length >= 2 &&
    CSV_KEY_HEADERS.has(firstCells[0]?.toLowerCase() ?? '') &&
    CSV_VALUE_HEADERS.has(firstCells[1]?.toLowerCase() ?? '');

  const dataLines = headerLooksLikeLabels ? lines.slice(1) : lines;

  for (const line of dataLines) {
    if (line.includes('=') && !line.includes(',')) {
      Object.assign(secrets, parseVaultImportDraft(line));
      continue;
    }

    const cells = splitCsvRow(line);
    if (cells.length < 2) {
      continue;
    }

    const name = cells[0]?.trim() ?? '';
    const value = cells.slice(1).join(',').trim();
    if (name && value) {
      secrets[name] = value;
    }
  }

  return secrets;
}

export function parseVaultImportJson(raw: string): Record<string, string> {
  const payload = JSON.parse(raw) as unknown;
  let entries: Record<string, unknown> = {};

  if (typeof payload === 'object' && payload !== null) {
    const record = payload as Record<string, unknown>;
    if (typeof record.secrets === 'object' && record.secrets !== null) {
      entries = record.secrets as Record<string, unknown>;
    } else {
      entries = record;
    }
  }

  const secrets: Record<string, string> = {};
  for (const [key, value] of Object.entries(entries)) {
    const name = String(key).trim();
    const text = String(value ?? '').trim();
    if (name && text) {
      secrets[name] = text;
    }
  }
  return secrets;
}

export function parseVaultImportExport(raw: string, filename = ''): Record<string, string> {
  const trimmed = raw.trim();
  if (!trimmed) {
    return {};
  }

  const lowerName = filename.toLowerCase();
  if (lowerName.endsWith('.json')) {
    return parseVaultImportJson(trimmed);
  }
  if (lowerName.endsWith('.csv') || lowerName.endsWith('.tsv')) {
    return parseVaultImportCsv(trimmed);
  }

  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return parseVaultImportJson(trimmed);
    } catch {
      return parseVaultImportDraft(trimmed);
    }
  }

  if (trimmed.includes(',') && trimmed.split('\n').some((line) => line.includes(','))) {
    return parseVaultImportCsv(trimmed);
  }

  return parseVaultImportDraft(trimmed);
}

export function summarizeVaultImportKeys(secrets: Record<string, string>): string {
  const names = Object.keys(secrets).sort();
  if (!names.length) {
    return 'No import keys parsed';
  }
  return `${names.length} key(s): ${names.join(', ')}`;
}

/** Axon / Bitwarden vault CSV exports (full secret rows, not monitor KEY=value). */
export function looksLikeAxonVaultCsv(raw: string): boolean {
  const firstLine = raw.trim().split(/\r?\n/)[0] ?? '';
  if (!firstLine.includes(',')) {
    return false;
  }
  const headers = new Set(firstLine.split(',').map((cell) => cell.trim().toLowerCase()));
  return (
    headers.has('name') &&
    (headers.has('password') || headers.has('category') || headers.has('login_password'))
  );
}

export function formatVaultFullImportMessage(
  result: Record<string, unknown>,
  sourceLabel: string,
): string {
  const added = Number(result.added ?? 0);
  const updated = Number(result.updated ?? 0);
  const skipped = Number(result.skipped ?? 0);
  const sourceCount = Number(result.source_secret_count ?? 0);
  const summary = `${added} added, ${updated} updated, ${skipped} skipped`;
  if (sourceCount > 0) {
    return `Imported ${sourceLabel} (${sourceCount} rows): ${summary}.`;
  }
  return `Imported ${sourceLabel}: ${summary}.`;
}
