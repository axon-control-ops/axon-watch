import type { Ref } from 'vue';

import {
  clearAgentShellMirror,
  pendingAgentBackgroundCommand,
  pendingOperatorTerminalCommand,
  takePendingAgentBackgroundCommand,
  takePendingOperatorTerminalCommand,
} from './agent-shell-mirror-state';

export type TerminalPendingHost = {
  writeInput?: (data: string) => void;
  exitMirrorMode?: () => void;
};

export type TerminalPendingSession = {
  id: string;
  role: string;
};

type FlushDeps = {
  sessions: readonly TerminalPendingSession[];
  activeSessionId: string;
  hosts: Record<string, TerminalPendingHost | null | undefined>;
  setVisibleSessionIds: (ids: string[]) => void;
};

function flushRoleCommand(input: {
  role: 'operator' | 'agent';
  pending: string | null;
  take: () => string | null;
  deps: FlushDeps;
  sessionId?: string;
  beforeWrite?: (host: TerminalPendingHost) => void;
}): void {
  if (!input.pending) {
    return;
  }
  const session = input.deps.sessions.find((item) => item.role === input.role);
  if (!session) {
    return;
  }
  if (input.sessionId && input.sessionId !== session.id) {
    return;
  }
  if (input.deps.activeSessionId !== session.id) {
    return;
  }
  const host = input.deps.hosts[session.id];
  if (!host?.writeInput) {
    return;
  }
  const command = input.take();
  if (!command) {
    return;
  }
  input.beforeWrite?.(host);
  input.deps.setVisibleSessionIds([session.id]);
  requestAnimationFrame(() => {
    host.writeInput?.(`${command}\r`);
  });
}

/** Inject a queued operator bash command into the focused operator PTY. */
export function flushPendingOperatorTerminalCommand(
  deps: FlushDeps,
  sessionId?: string,
): void {
  flushRoleCommand({
    role: 'operator',
    pending: pendingOperatorTerminalCommand.value,
    take: takePendingOperatorTerminalCommand,
    deps,
    sessionId,
  });
}

/** Inject a Continue-in-background command into the focused vaxon agent PTY. */
export function flushPendingAgentBackgroundTerminalCommand(
  deps: FlushDeps,
  sessionId?: string,
): void {
  flushRoleCommand({
    role: 'agent',
    pending: pendingAgentBackgroundCommand.value,
    take: takePendingAgentBackgroundCommand,
    deps,
    sessionId,
    beforeWrite: (host) => {
      clearAgentShellMirror();
      host.exitMirrorMode?.();
    },
  });
}

export function focusSessionForPendingCommand(input: {
  role: 'operator' | 'agent';
  sessions: readonly TerminalPendingSession[];
  activeSessionId: string;
  setActiveSessionId: (id: string) => void;
  setVisibleSessionIds: (ids: string[]) => void;
}): TerminalPendingSession | null {
  const session = input.sessions.find((item) => item.role === input.role);
  if (!session) {
    return null;
  }
  input.setVisibleSessionIds([session.id]);
  if (input.activeSessionId !== session.id) {
    input.setActiveSessionId(session.id);
  }
  return session;
}

/** Watch helper: keep pending refs typed for WorkbenchTerminalDock. */
export type PendingCommandRef = Ref<string | null>;
