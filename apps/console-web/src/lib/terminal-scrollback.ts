import type { Terminal } from '@xterm/xterm';

export const TERMINAL_SCROLLBACK_PREFIX = 'axon-xterm-scrollback-v4:';
export const MAX_TERMINAL_SCROLLBACK_CHARS = 256_000;

const SCROLLBACK_SCAFFOLD_LINE =
  /^\[(terminal|attached|context)\]/;

const ANSI_ESCAPE_PATTERN = /\x1b\[[0-9;]*m/g;

const SINGLE_SHELL_PROMPT_LINE = /^[^\s]+@[^\s:]+:.*\$\s*$/;

const CONCATENATED_SHELL_PROMPT_LINE = /^([^\s]+@[^\s:]+:.*\$\s*)+$/;

export function stripAnsi(text: string): string {
  return text.replace(ANSI_ESCAPE_PATTERN, '');
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
  sessionStorage.removeItem(scrollbackStorageKey(workspaceId, sessionId));
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
