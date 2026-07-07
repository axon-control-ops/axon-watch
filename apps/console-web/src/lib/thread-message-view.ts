import type { ThreadMessageRole } from './operator-thread';

export function formatThreadTimestamp(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return iso;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(parsed));
}

export function formatThreadRole(role: ThreadMessageRole): string {
  return role.toUpperCase();
}

export function shortenRunId(runId: string): string {
  const trimmed = runId.trim();
  if (trimmed.length <= 14) {
    return trimmed;
  }
  return `${trimmed.slice(0, 10)}…`;
}

export function agentContentLooksLikeErrorDump(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (/401\s+Unauthorized|Incorrect API key/i.test(trimmed)) {
    return true;
  }
  if (trimmed.startsWith('{') && /"error"\s*:/.test(trimmed)) {
    return true;
  }
  if (trimmed.length > 1800 && /(\{|\[)/.test(trimmed)) {
    return true;
  }
  return false;
}

export function summarizeAgentErrorContent(content: string): string {
  const trimmed = content.trim();
  if (!trimmed) {
    return trimmed;
  }

  const lines = trimmed.split('\n').map((line) => line.trim()).filter(Boolean);
  const headline = lines.find(
    (line) =>
      !line.startsWith('{') &&
      !line.startsWith('[') &&
      !line.startsWith('"') &&
      line.length <= 240,
  );
  if (headline) {
    return headline;
  }

  const unauthorized = trimmed.match(/401[^\n]*/i)?.[0];
  if (unauthorized) {
    return unauthorized.replace(/\s+/g, ' ').slice(0, 220);
  }

  return `${trimmed.slice(0, 220).trim()}…`;
}

export function shouldDefaultAgentPreview(content: string): boolean {
  if (agentContentLooksLikeErrorDump(content)) {
    return false;
  }
  return true;
}

export function systemMessagePreview(content: string): string {
  const trimmed = content.trim();
  if (!trimmed) {
    return trimmed;
  }
  if (trimmed.length <= 120) {
    return trimmed;
  }
  return `${trimmed.slice(0, 117).trim()}…`;
}

export function shouldCollapseSystemMessage(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.startsWith('Lane B (')) {
    return true;
  }
  if (/^Run run_\S+ dispatched/i.test(trimmed)) {
    return true;
  }
  if (/^Command linked to run run_/i.test(trimmed)) {
    return true;
  }
  return trimmed.length > 120;
}
