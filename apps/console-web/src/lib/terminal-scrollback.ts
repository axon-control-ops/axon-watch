import type { Terminal } from '@xterm/xterm';

export const TERMINAL_SCROLLBACK_PREFIX = 'axon-xterm-scrollback-v4:';
export const MAX_TERMINAL_SCROLLBACK_CHARS = 256_000;

const SCROLLBACK_SCAFFOLD_LINE =
  /^\[(terminal|attached|context)\]/;

const ANSI_ESCAPE_PATTERN = /\x1b\[[0-9;]*m/g;
const CSI_SEQUENCE_PATTERN =
  /\u001b(?:\u009b)?[[\]()#;?]*(?:\d{1,4}(?:;\d{0,4})*)?[\dA-PRZcf-nqry=><~]/g;
const OSC_SEQUENCE_PATTERN = /\u001b\][^\u0007]*(?:\u0007|\u001b\\)/g;
const ORPHAN_CSI_PATTERN = /(?:\uFFFD)?(?:\[[0-9;?]*[A-Za-z])+/g;
const ORPHAN_CSI_ONLY_LINE =
  /^[\s\uFFFD]*(?:\[[0-9;?]*[A-Za-z][\s\uFFFD]*)+$/;

const SINGLE_SHELL_PROMPT_LINE = /^[^\s]+@[^\s:]+:.*\$\s*$/;

const CONCATENATED_SHELL_PROMPT_LINE = /^([^\s]+@[^\s:]+:.*\$\s*)+$/;

export function stripAnsi(text: string): string {
  return String(text || '')
    .replace(OSC_SEQUENCE_PATTERN, '')
    .replace(CSI_SEQUENCE_PATTERN, '')
    .replace(ANSI_ESCAPE_PATTERN, '')
    .replace(/\u001b./g, '')
    .replace(/\u009b[[\]()#;?]*(?:\d{1,4}(?:;\d{0,4})*)?[\dA-PRZcf-nqry=><~]/g, '');
}

/** Strip CSI fragments when the ESC byte was lost in tee/storage (Jest cursor spam). */
export function stripOrphanAnsiFragments(text: string): string {
  const stripped = String(text || '').replace(ORPHAN_CSI_PATTERN, '');
  return stripped
    .split('\n')
    .filter((line) => !ORPHAN_CSI_ONLY_LINE.test(line))
    .join('\n');
}

function lineLooksAnsiPolluted(line: string): boolean {
  const trimmed = line.trim();
  return (
    /\u001b/.test(line) ||
    /\[[0-9]+[A-Z]/.test(line) ||
    ORPHAN_CSI_ONLY_LINE.test(trimmed) ||
    (line.match(/\[[0-9;?]*[A-Za-z]/g)?.length ?? 0) >= 2
  );
}

export function cleanTerminalDisplayLine(line: string): string {
  let cleaned = stripAnsi(line);
  if (lineLooksAnsiPolluted(line)) {
    cleaned = stripOrphanAnsiFragments(cleaned).replace(/\[[0-9;?]*[A-Za-z]/g, '');
  }
  return cleaned.trimEnd();
}

/** Jest/npm test scrollback: drop cursor-rewrite noise, keep pass/fail + summaries. */
export function compactTestRunnerOutput(text: string): string {
  const lines = String(text || '')
    .split('\n')
    .map((line) => cleanTerminalDisplayLine(line));
  const kept: string[] = [];
  const summaries = new Map<string, string>();
  const seen = new Set<string>();

  const remember = (line: string): void => {
    const key = line.trim();
    if (!key || seen.has(key)) {
      return;
    }
    seen.add(key);
    kept.push(line.trimEnd());
  };

  for (const line of lines) {
    const trimmed = line.trimEnd();
    if (!trimmed.trim()) {
      continue;
    }
    if (/^(PASS|FAIL)\s+\S/.test(trimmed)) {
      remember(trimmed);
      continue;
    }
    const summaryMatch = /^(Test Suites:|Tests:|Snapshots:|Time:)/.exec(trimmed);
    if (summaryMatch) {
      summaries.set(summaryMatch[1], trimmed.trim());
      continue;
    }
    if (/^\s*(✓|✕|○|●)/.test(trimmed) || /\(\d+\s*m?s\)\s*$/.test(trimmed)) {
      remember(trimmed);
      continue;
    }
    if (/^RUNS\s/.test(trimmed) && !/PASS|FAIL/.test(trimmed)) {
      continue;
    }
    if (/Test Suites:|Tests:|Snapshots:/i.test(trimmed)) {
      continue;
    }
    if (trimmed.length > 1) {
      remember(trimmed);
    }
  }

  for (const summary of summaries.values()) {
    remember(summary);
  }

  return kept.join('\n').trim();
}

export function sanitizeTerminalDisplayOutput(text: string, command = ''): string {
  const normalized = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const cleaned = normalized
    .split('\n')
    .map((line) => cleanTerminalDisplayLine(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/^\n+|\n+$/g, '');

  if (/\bnpm\s+test\b|\bnpx\s+jest\b|\bjest\b/i.test(command)) {
    const compact = compactTestRunnerOutput(cleaned);
    return compact || cleaned;
  }
  return cleaned;
}

export function isShellPromptLine(line: string): boolean {
  const plain = stripAnsi(line).trimEnd();
  if (!plain) {
    return false;
  }

  return (
    SINGLE_SHELL_PROMPT_LINE.test(plain) || CONCATENATED_SHELL_PROMPT_LINE.test(plain)
  );
}

export function sanitizeScrollbackText(text: string): string {
  return text
    .split('\n')
    .filter((line) => !SCROLLBACK_SCAFFOLD_LINE.test(line.trim()))
    .filter((line) => !isShellPromptLine(line))
    .join('\n')
    .trimEnd();
}

export function scrollbackStorageKey(workspaceId: string, sessionId = 'terminal-operator'): string {
  return `${TERMINAL_SCROLLBACK_PREFIX}${workspaceId}:${sessionId}`;
}

export function migrateTerminalScrollback(workspaceId: string, sessionId = 'terminal-operator'): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  sessionStorage.removeItem(`axon-xterm-scrollback-v1:${workspaceId}`);
  sessionStorage.removeItem(`axon-xterm-scrollback-v2:${workspaceId}`);
  sessionStorage.removeItem(`axon-xterm-scrollback-v3:${workspaceId}`);
}

export function serializeTerminalBuffer(terminal: Terminal): string {
  const buffer = terminal.buffer.active;
  const lines: string[] = [];

  for (let index = 0; index < buffer.length; index += 1) {
    const line = buffer.getLine(index);
    if (line) {
      lines.push(line.translateToString(true));
    }
  }

  return sanitizeScrollbackText(lines.join('\n')).slice(-MAX_TERMINAL_SCROLLBACK_CHARS);
}

export function persistTerminalScrollback(
  workspaceId: string,
  terminal: Terminal,
  sessionId = 'terminal-operator',
): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  try {
    const serialized = serializeTerminalBuffer(terminal);
    const key = scrollbackStorageKey(workspaceId, sessionId);
    if (!serialized) {
      sessionStorage.removeItem(key);
      return;
    }

    sessionStorage.setItem(key, serialized);
  } catch {
    // Ignore quota errors; scrollback persistence is best-effort.
  }
}

export function restoreTerminalScrollback(
  workspaceId: string,
  terminal: Terminal,
  sessionId = 'terminal-operator',
): boolean {
  if (typeof sessionStorage === 'undefined') {
    return false;
  }

  const saved = sanitizeScrollbackText(
    sessionStorage.getItem(scrollbackStorageKey(workspaceId, sessionId)) ?? '',
  );
  if (!saved) {
    return false;
  }

  terminal.write(saved);
  if (!saved.endsWith('\n')) {
    terminal.write('\r\n');
  }

  return true;
}
