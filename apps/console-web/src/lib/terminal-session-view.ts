export interface TerminalSessionRecord {
  session_id: string;
  workspace_id: string;
  role: 'operator' | 'agent' | string;
  title: string;
  run_id: string | null;
  created_at: string;
  /** Directory the PTY is really rooted at (isolated lanes differ from the bound root). */
  cwd?: string;
  /** Branch checked out at `cwd` — not necessarily the bound workspace branch. */
  branch?: string;
  /** True when this lane runs in the disposable Sandbox checkout. */
  isolated?: boolean;
}

export const SANDBOX_TERMINAL_SESSION_ID = 'terminal-sandbox';

export const DEFAULT_OPERATOR_TERMINAL_SESSION_ID = 'terminal-operator';
export const DEFAULT_VAXON_TERMINAL_TITLE = 'vaxon';

function detectShellLabel(): string {
  // Operator PTY default is zsh on this stack; only fall back to bash if
  // the browser is clearly not a unix-like host.
  if (typeof navigator === 'undefined') {
    return 'zsh';
  }
  const platform = String(navigator.platform || '').toLowerCase();
  if (platform.includes('win')) {
    return 'bash';
  }
  return 'zsh';
}

export function terminalSessionTabLabel(session: TerminalSessionRecord): string {
  const title = session.title?.trim() || '';
  if (session.role === 'agent') {
    if (!title || /^agent(\s+shell)?$/i.test(title)) {
      return DEFAULT_VAXON_TERMINAL_TITLE;
    }
    return title === DEFAULT_VAXON_TERMINAL_TITLE ? 'vaxon · agent' : title;
  }
  if (!title || /^terminal$/i.test(title)) {
    return `${detectShellLabel()} · local`;
  }
  if (/^(zsh|bash)$/i.test(title)) {
    return `${title.toLowerCase()} · local`;
  }
  return title;
}

/**
 * Branch badge for a terminal tab.
 *
 * Only isolated lanes get one. Showing the bound branch on every tab is what
 * made the dock misleading in the first place: an operator reading
 * `development` on a tab whose PTY sits in a `worker/...` worktree concludes
 * the agent is working on the bound branch.
 */
export function terminalSessionBranchBadge(session: TerminalSessionRecord): string {
  if (!session.isolated) return '';
  return session.branch?.trim() || 'isolated';
}

/** Full cwd + branch, for the tab's hover title. */
export function terminalSessionRootTitle(session: TerminalSessionRecord): string {
  const cwd = session.cwd?.trim() || '';
  const branch = session.branch?.trim() || '';
  if (!cwd && !branch) return '';
  const where = session.isolated ? 'Sandbox checkout' : 'Bound workspace';
  return [`${where}: ${cwd || 'unknown'}`, branch ? `branch ${branch}` : ''].filter(Boolean).join(' · ');
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
