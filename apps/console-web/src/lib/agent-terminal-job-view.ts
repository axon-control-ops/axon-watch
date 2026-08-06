/**
 * Compact presentation for axon-agent-terminal-job / OTA shell cards.
 * Status polls dump JSON; live jobs tee `# axon-job:<id>` fences — both should
 * read as job receipts, not raw shell noise.
 */

export type AgentTerminalJobKind = 'job_status' | 'job_stream' | 'shell';

export type AgentTerminalJobView = {
  kind: AgentTerminalJobKind;
  jobId: string | null;
  status: string | null;
  /** Short command label for chips (e.g. npm run ota:canary). */
  commandLabel: string | null;
  /** One-line header chip text. */
  headline: string | null;
  /** Cleaned body for <pre> / xterm mirror. */
  displayOutput: string;
  /** Compact key/value rows for status JSON cards. */
  summaryRows: Array<{ label: string; value: string }>;
  isOta: boolean;
  isStatusPoll: boolean;
};

/** Bound main-thread work — OTA streams can be multi‑MB with \r progress spam. */
export const AGENT_TERMINAL_JOB_OUTPUT_CAP = 48_000;

const AXON_JOB_MARKER_RE = /#\s*axon-job:([A-Za-z0-9._:-]+)/;
const STATUS_POLL_RE = /axon-agent-terminal-job(?:\.sh)?\s+--status\b/i;
const OTA_RE = /\bota(?::|\/|\b)|eas\s+update|expo(?:-cli)?\b/i;
const ZSHENV_NOISE_RE =
  /^[^\n]*\.zshenv:[^\n]*(?:no such file or directory|\/\.cargo\/env)[^\n]*$/gim;
const CARGO_ENV_NOISE_RE = /^[^\n]*\/\.cargo\/env[^\n]*$/gim;

function normalizeNewlines(text: string): string {
  return String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
}

/** Keep the useful tail of huge streams before regex / JSON work. */
export function capTerminalJobOutput(
  text: string,
  cap = AGENT_TERMINAL_JOB_OUTPUT_CAP,
): string {
  const raw = String(text || '');
  if (raw.length <= cap) {
    return raw;
  }
  const markerMatch = AXON_JOB_MARKER_RE.exec(raw);
  const markerLine = markerMatch ? `# axon-job:${markerMatch[1]}\n` : '';
  const tailBudget = Math.max(1_024, cap - markerLine.length);
  return `${markerLine}${raw.slice(raw.length - tailBudget)}`;
}

/** Drop host shell noise that otherwise dominates OTA status cards. */
export function stripTerminalJobNoise(text: string): string {
  return normalizeNewlines(text)
    .replace(ZSHENV_NOISE_RE, '')
    .replace(CARGO_ENV_NOISE_RE, '')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/^\n+|\n+$/g, '');
}

export function extractAxonJobId(command: string, output: string): string | null {
  const fromOutput = AXON_JOB_MARKER_RE.exec(output);
  if (fromOutput?.[1]) {
    return fromOutput[1];
  }
  const fromStatus =
    /axon-agent-terminal-job(?:\.sh)?\s+--status\s+([A-Za-z0-9._:-]+)/i.exec(command);
  if (fromStatus?.[1]) {
    return fromStatus[1];
  }
  const bare = /\b(agent-job-[A-Za-z0-9._:-]+)\b/.exec(`${command}\n${output}`);
  return bare?.[1] ?? null;
}

export function shortenTerminalCommandLabel(command: string): string {
  const raw = String(command || '').trim();
  if (!raw) {
    return '';
  }
  // Strip leading ENV= assignments for display.
  const withoutEnv = raw.replace(/^(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)+/, '').trim();
  const otaMatch = /\bnpm\s+run\s+ota(?::[A-Za-z0-9_-]+)?\b/i.exec(withoutEnv);
  if (otaMatch) {
    return otaMatch[0];
  }
  if (withoutEnv.length <= 72) {
    return withoutEnv;
  }
  return `${withoutEnv.slice(0, 69)}…`;
}

function tryParseJsonObject(text: string): Record<string, unknown> | null {
  const cleaned = stripTerminalJobNoise(text).trim();
  if (!cleaned.startsWith('{')) {
    // Status polls often print noise then JSON.
    const start = cleaned.indexOf('{');
    const end = cleaned.lastIndexOf('}');
    if (start < 0 || end <= start) {
      return null;
    }
    try {
      const parsed = JSON.parse(cleaned.slice(start, end + 1)) as unknown;
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : null;
    } catch {
      return null;
    }
  }
  try {
    const parsed = JSON.parse(cleaned) as unknown;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function looksLikeJobStatus(record: Record<string, unknown>): boolean {
  const jobId = record.job_id ?? record.jobId;
  const status = record.status;
  return typeof jobId === 'string' || typeof status === 'string';
}

function formatStatusRows(record: Record<string, unknown>): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  const pick = (label: string, key: string): void => {
    const value = record[key];
    if (value == null || value === '') {
      return;
    }
    rows.push({ label, value: String(value) });
  };
  pick('Status', 'status');
  pick('Job', 'job_id');
  if (!rows.some((row) => row.label === 'Job')) {
    pick('Job', 'jobId');
  }
  pick('Workspace', 'workspace_id');
  pick('Session', 'session_id');
  pick('Command', 'command');
  pick('Exit', 'exit_code');
  pick('Updated', 'updated_at');
  pick('Started', 'started_at');
  return rows.slice(0, 8);
}

function formatJobStatusDisplay(record: Record<string, unknown>): string {
  return formatStatusRows(record)
    .map((row) => `${row.label}: ${row.value}`)
    .join('\n');
}

/** Prefer progress / export lines near the end for live OTA streams. */
export function prioritizeTerminalJobTail(output: string, maxLines = 40): string {
  const cleaned = stripTerminalJobNoise(output);
  if (!cleaned) {
    return '';
  }
  const lines = cleaned.split('\n');
  if (lines.length <= maxLines) {
    return cleaned;
  }
  const progress = lines.filter((line) =>
    /(?:████|▓|░|%\s*\(|Exporting|Uploading|Published|expo-cli|eas-cli|ota)/i.test(line),
  );
  const marker = lines.find((line) => AXON_JOB_MARKER_RE.test(line));
  const tail = lines.slice(-Math.max(12, maxLines - progress.length - 2));
  const merged: string[] = [];
  const seen = new Set<string>();
  if (marker) {
    merged.push(marker);
    seen.add(marker);
  }
  for (const line of [...progress.slice(-8), ...tail]) {
    if (seen.has(line)) {
      continue;
    }
    seen.add(line);
    merged.push(line);
  }
  return merged.join('\n');
}

/** True only when the card needs job/OTA formatting (avoid work on ordinary shells). */
export function looksLikeAgentTerminalJob(command: string, output: string): boolean {
  const cmd = String(command || '');
  if (STATUS_POLL_RE.test(cmd)) {
    return true;
  }
  if (/\bagent-job-[A-Za-z0-9._:-]+\b/i.test(cmd)) {
    return true;
  }
  // Probe a bounded head/tail — full-body scans freeze Dana-sized histories.
  const raw = String(output || '');
  const probe =
    raw.length <= 4_000 ? raw : `${raw.slice(0, 2_000)}\n${raw.slice(-2_000)}`;
  if (/#\s*axon-job:/i.test(probe) || /\bagent-job-[A-Za-z0-9._:-]+\b/i.test(probe)) {
    return true;
  }
  if (/"job_id"\s*:/.test(probe) && /"status"\s*:/.test(probe)) {
    return true;
  }
  return false;
}

export function buildAgentTerminalJobView(input: {
  command: string;
  output: string;
}): AgentTerminalJobView {
  const command = String(input.command || '');
  const commandLabel = shortenTerminalCommandLabel(command) || null;
  const isStatusPoll = STATUS_POLL_RE.test(command);

  // Fast path: ordinary shell cards — no regex noise stripping / JSON parse.
  if (!looksLikeAgentTerminalJob(command, input.output || '')) {
    const output = normalizeNewlines(capTerminalJobOutput(input.output || '')).trim();
    return {
      kind: 'shell',
      jobId: null,
      status: null,
      commandLabel,
      headline: null,
      displayOutput: output,
      summaryRows: [],
      isOta: OTA_RE.test(command),
      isStatusPoll: false,
    };
  }

  // Cap before normalize/regex — status polls stay small; live OTA can be huge.
  const capped = capTerminalJobOutput(input.output || '');
  const output = normalizeNewlines(capped);
  const cleaned = stripTerminalJobNoise(output);
  const jobId = extractAxonJobId(command, output);
  // Only parse JSON for status polls or short bodies — never scan multi‑MB streams.
  const json =
    isStatusPoll || cleaned.trimStart().startsWith('{') || cleaned.length < 8_000
      ? tryParseJsonObject(cleaned)
      : null;
  const isOta =
    OTA_RE.test(command) ||
    OTA_RE.test(cleaned.slice(0, 2_000)) ||
    Boolean(json && typeof json.command === 'string' && OTA_RE.test(String(json.command)));

  if (json && (isStatusPoll || looksLikeJobStatus(json))) {
    const status = typeof json.status === 'string' ? json.status : null;
    const resolvedJobId =
      (typeof json.job_id === 'string' && json.job_id) ||
      (typeof json.jobId === 'string' && json.jobId) ||
      jobId;
    const cmd =
      (typeof json.command === 'string' && shortenTerminalCommandLabel(json.command)) ||
      commandLabel;
    const summaryRows = formatStatusRows(json);
    return {
      kind: 'job_status',
      jobId: resolvedJobId,
      status,
      commandLabel: cmd,
      headline: [status || 'status', resolvedJobId, cmd].filter(Boolean).join(' · '),
      displayOutput: formatJobStatusDisplay(json),
      summaryRows,
      isOta: isOta || Boolean(cmd && OTA_RE.test(cmd)),
      isStatusPoll: true,
    };
  }

  if (jobId || /#\s*axon-job:/i.test(output)) {
    const statusMatch = /\bstatus[=:]\s*([A-Za-z_]+)/i.exec(cleaned);
    const status = statusMatch?.[1]?.toLowerCase() ?? null;
    return {
      kind: 'job_stream',
      jobId,
      status,
      commandLabel,
      headline: [isOta ? 'OTA' : 'Job', jobId, status].filter(Boolean).join(' · '),
      displayOutput: prioritizeTerminalJobTail(cleaned),
      summaryRows: [],
      isOta,
      isStatusPoll: false,
    };
  }

  return {
    kind: 'shell',
    jobId: null,
    status: null,
    commandLabel,
    headline: null,
    displayOutput: cleaned || output.trim(),
    summaryRows: [],
    isOta,
    isStatusPoll: false,
  };
}
