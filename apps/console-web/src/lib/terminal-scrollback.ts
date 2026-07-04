import type { Terminal } from '@xterm/xterm';

export const TERMINAL_SCROLLBACK_PREFIX = 'axon-xterm-scrollback-v2:';
export const MAX_TERMINAL_SCROLLBACK_CHARS = 256_000;

const SCROLLBACK_SCAFFOLD_LINE =
  /^\[(terminal|attached|context)\]/;

export function sanitizeScrollbackText(text: string): string {
  return text
    .split('\n')
    .filter((line) => !SCROLLBACK_SCAFFOLD_LINE.test(line.trim()))
    .join('\n')
    .trimEnd();
}

export function migrateTerminalScrollback(workspaceId: string): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  sessionStorage.removeItem(`axon-xterm-scrollback-v1:${workspaceId}`);
}

export function scrollbackStorageKey(workspaceId: string): string {
  return `${TERMINAL_SCROLLBACK_PREFIX}${workspaceId}`;
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

export function persistTerminalScrollback(workspaceId: string, terminal: Terminal): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }

  try {
    sessionStorage.setItem(scrollbackStorageKey(workspaceId), serializeTerminalBuffer(terminal));
  } catch {
    // Ignore quota errors; scrollback persistence is best-effort.
  }
}

export function restoreTerminalScrollback(workspaceId: string, terminal: Terminal): boolean {
  if (typeof sessionStorage === 'undefined') {
    return false;
  }

  const saved = sanitizeScrollbackText(sessionStorage.getItem(scrollbackStorageKey(workspaceId)) ?? '');
  if (!saved) {
    return false;
  }

  terminal.write(saved);
  if (!saved.endsWith('\n')) {
    terminal.write('\r\n');
  }

  return true;
}
