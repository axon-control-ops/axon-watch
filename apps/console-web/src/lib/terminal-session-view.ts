export interface TerminalSessionRecord {
  session_id: string;
  workspace_id: string;
  role: 'operator' | 'agent' | string;
  title: string;
  run_id: string | null;
  created_at: string;
}

export const DEFAULT_OPERATOR_TERMINAL_SESSION_ID = 'terminal-operator';

export function terminalSessionTabLabel(session: TerminalSessionRecord): string {
  return session.title?.trim() || (session.role === 'agent' ? 'Agent shell' : 'Terminal');
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
