/** Human-readable Debug Mode log lines (Cursor-style evidence feed). */

export type DebugSessionLogViewEntry = {
  hypothesisId?: string;
  location?: string;
  message?: string;
  data?: Record<string, unknown>;
  timestamp?: number | string;
  [key: string]: unknown;
};

export type FormattedDebugSessionLog = {
  hypothesisLabel: string;
  title: string;
  details: string[];
  locationShort: string;
};

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function shortenId(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) {
    return null;
  }
  const text = value.trim();
  if (UUID_RE.test(text)) {
    return text.slice(0, 8);
  }
  if (text.length > 28) {
    return `${text.slice(0, 24)}…`;
  }
  return text;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function formatDataValue(key: string, value: unknown): string | null {
  if (value == null) {
    return null;
  }
  if (typeof value === 'boolean') {
    if (key === 'hasRefresh') {
      return value ? 'has refresh token' : 'missing refresh token';
    }
    if (key === 'invalidRefresh') {
      return value ? 'invalid refresh token' : null;
    }
    if (key === 'success') {
      return value ? 'succeeded' : 'failed';
    }
    if (key === 'requiresPassword') {
      return value ? 'password required' : null;
    }
    if (key === 'switchInProgress') {
      return value ? 'switch in progress' : null;
    }
    if (key === 'switchPending') {
      return value ? 'switch pending' : null;
    }
    if (key === 'willRevokeOthers') {
      return value ? 'will revoke other sessions' : 'skip revoke others';
    }
    if (key === 'singleSessionEnabled') {
      return value ? 'single-session on' : 'single-session off';
    }
    if (key === 'sessionRestored') {
      return value ? 'session restored' : 'session not restored';
    }
    if (key === 'ok') {
      return value ? 'ok' : 'not ok';
    }
    return value ? humanizeKey(key) : `not ${humanizeKey(key)}`;
  }

  if (typeof value === 'number') {
    return `${humanizeKey(key)} ${value}`;
  }

  if (typeof value === 'string') {
    if (!value.trim()) {
      return null;
    }
    if (key === 'logLabel') {
      return null;
    }
    if (key === 'error') {
      return value;
    }
    if (/userId|UserId|from|to|target|active/i.test(key)) {
      const short = shortenId(value);
      if (!short) {
        return null;
      }
      if (key === 'targetUserId' || key === 'to') {
        return `target ${short}`;
      }
      if (key === 'activeUserId' || key === 'from') {
        return `from ${short}`;
      }
      if (key === 'gotUserId') {
        return `got ${short}`;
      }
      if (key === 'userId') {
        return `user ${short}`;
      }
      return `${humanizeKey(key)} ${short}`;
    }
    if (key === 'method' || key === 'platform' || key === 'path' || key === 'reason') {
      return `${humanizeKey(key)} ${value}`;
    }
    const short = shortenId(value) ?? value;
    return `${humanizeKey(key)} ${short}`;
  }

  return null;
}

export function shortDebugLocation(location: string | undefined): string {
  const text = (location || '').trim();
  if (!text) {
    return '';
  }
  const withoutPath = text.includes('/') ? (text.split('/').pop() ?? text) : text;
  const parts = withoutPath.split('.');
  if (parts.length >= 2) {
    return parts.slice(-1)[0] || withoutPath;
  }
  return withoutPath;
}

/**
 * Turn one NDJSON evidence line into a Cursor-like human summary.
 * Avoid dumping raw JSON into the Runtime logs feed.
 */
export function formatDebugSessionLogEntry(
  entry: DebugSessionLogViewEntry,
): FormattedDebugSessionLog {
  const hypothesis = String(entry.hypothesisId ?? '').trim();
  const hypothesisLabel = hypothesis
    ? hypothesis.toUpperCase().startsWith('H')
      ? hypothesis.toUpperCase()
      : `H${hypothesis}`
    : 'LOG';

  const title = String(entry.message ?? 'Runtime event').trim() || 'Runtime event';
  const data =
    entry.data && typeof entry.data === 'object' && !Array.isArray(entry.data)
      ? entry.data
      : {};

  const details: string[] = [];
  const seen = new Set<string>();
  for (const [key, value] of Object.entries(data)) {
    const part = formatDataValue(key, value);
    if (!part || seen.has(part)) {
      continue;
    }
    seen.add(part);
    details.push(part);
    if (details.length >= 5) {
      break;
    }
  }

  return {
    hypothesisLabel,
    title,
    details,
    locationShort: shortDebugLocation(
      typeof entry.location === 'string' ? entry.location : undefined,
    ),
  };
}
