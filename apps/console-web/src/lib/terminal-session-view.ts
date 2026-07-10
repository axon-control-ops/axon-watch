export interface TerminalSessionRecord {
  session_id: string;
  workspace_id: string;
  role: 'operator' | 'agent' | string;
  title: string;
  run_id: string | null;
  created_at: string;
}

export const DEFAULT_OPERATOR_TERMINAL_SESSION_ID = 'terminal-operator';
export const DEFAULT_VAXON_TERMINAL_TITLE = 'vaxon';

function detectShellLabel(): string {
  if (typeof navigator === 'undefined') {
    return 'bash';
  }
  const platform = String(navigator.platform || '').toLowerCase();
  // Browser can't know the remote shell for sure; prefer zsh on mac-like hosts.
  if (platform.includes('mac')) {
    return 'zsh';
  }
  return 'bash';
}

export function terminalSessionTabLabel(session: TerminalSessionRecord): string {
  const title = session.title?.trim() || '';
  if (session.role === 'agent') {
    if (!title || /^agent(\s+shell)?$/i.test(title)) {
      return DEFAULT_VAXON_TERMINAL_TITLE;
    }
    return title;
  }
  if (!title || /^terminal$/i.test(title)) {
    return detectShellLabel();
  }
  return title;
}

export function sortTerminalSessionsOperatorFirst(
  sessions: TerminalSessionRecord[],
): TerminalSessionRecord[] {
  return [...sessions].sort((left, right) => {
    if (left.session_id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID) {
      return -1;
    }
    if (right.session_id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID) {
      return 1;
    }
    return left.created_at.localeCompare(right.created_at);
  });
}

export function upsertTerminalSession(
  sessions: TerminalSessionRecord[],
  next: TerminalSessionRecord,
): TerminalSessionRecord[] {
  const without = sessions.filter((session) => session.session_id !== next.session_id);
  return sortTerminalSessionsOperatorFirst([...without, next]);
}
