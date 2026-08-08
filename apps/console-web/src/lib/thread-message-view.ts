import { agentMessageLooksLikeMarkdown } from './agent-message-markdown';
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
  if (role === 'operator') {
    return 'OP';
  }
  if (role === 'agent') {
    return 'AGENT';
  }
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
  // Large runtime JSON dumps — not long agent markdown with links or lists.
  if (trimmed.length > 1800 && !agentMessageLooksLikeMarkdown(trimmed)) {
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      return true;
    }
    if (/\{[\s\S]*"error"\s*:/.test(trimmed)) {
      return true;
    }
  }
  return false;
}

// A runtime fallback ("the CLI could not run") is delivered as an ordinary
// assistant message, so it renders identically to a real answer and an
// operator has to read it closely to notice nothing actually ran. This keys
// off the exact shape services/control-plane/app/cli_runtime/runtime_failure.py
// ::fallback_reply always produces; tests/test_runtime_fallback_marker_contract.py
// pins the two sides together, so reword one and that test fails.
const RUNTIME_FALLBACK_PREFIX = 'Lane B (';
const RUNTIME_FALLBACK_VERBS = ['failed on ', 'could not start', 'cannot start because'];

export function agentContentLooksLikeRuntimeFallback(content: string): boolean {
  const text = String(content || '')
    .split(/\s+/)
    .join(' ')
    .trim();
  if (!text.startsWith(RUNTIME_FALLBACK_PREFIX)) {
    return false;
  }
  return RUNTIME_FALLBACK_VERBS.some((verb) => text.includes(verb));
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
