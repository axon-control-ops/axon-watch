import { computed, type Ref } from 'vue';

import {
  createWorkspaceTerminalSession,
  deleteWorkspaceTerminalSession,
  fetchWorkspaceTerminalSessions,
  renameWorkspaceTerminalSession,
  type TerminalSessionRecord,
} from '../api/control-plane';
import { armAgentShellMirror, queueOperatorTerminalCommand } from './agent-shell-mirror-state';
import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
  upsertTerminalSession,
} from './terminal-session-view';

export interface TerminalSessionDescriptor {
  id: string;
  title: string;
  role: 'operator' | 'agent' | string;
  runId: string | null;
  state: 'ready';
}

export const DEFAULT_TERMINAL_SESSIONS: TerminalSessionDescriptor[] = [
  {
    id: DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
    title: 'bash',
    role: 'operator',
    runId: null,
    state: 'ready',
  },
];

interface TerminalSessionStoreInput {
  currentWorkspace: Ref<{ workspace_id: string } | null | undefined>;
  terminalSessions: Ref<TerminalSessionDescriptor[]>;
  activeTerminalSessionId: Ref<string>;
  ideAgentRunId: Ref<string | null>;
  revealIdeTerminalPanel: () => void;
}

function mapTerminalSessionRecord(record: TerminalSessionRecord): TerminalSessionDescriptor {
  return {
    id: record.session_id,
    title: record.title,
    role: record.role,
    runId: record.run_id,
    state: 'ready',
  };
}

export function createTerminalSessionStore(input: TerminalSessionStoreInput) {
  const activeTerminalSession = computed(
    () =>
      input.terminalSessions.value.find((session) => session.id === input.activeTerminalSessionId.value) ??
      DEFAULT_TERMINAL_SESSIONS[0],
  );

  async function loadTerminalSessions(workspaceId: string): Promise<void> {
    try {
      const snapshot = await fetchWorkspaceTerminalSessions(workspaceId);
      const mapped = snapshot.items.map((item) => mapTerminalSessionRecord(item));
      input.terminalSessions.value = mapped.length ? mapped : [...DEFAULT_TERMINAL_SESSIONS];
      if (!input.terminalSessions.value.some((session) => session.id === input.activeTerminalSessionId.value)) {
        input.activeTerminalSessionId.value = DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
      }
    } catch {
      input.terminalSessions.value = [...DEFAULT_TERMINAL_SESSIONS];
      input.activeTerminalSessionId.value = DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
    }
  }

  function setActiveTerminalSession(sessionId: string): void {
    if (!input.terminalSessions.value.some((session) => session.id === sessionId)) {
      return;
    }
    input.activeTerminalSessionId.value = sessionId;
    input.revealIdeTerminalPanel();
  }

  function applyTerminalSession(record: TerminalSessionRecord): void {
    const existingRecords: TerminalSessionRecord[] = input.terminalSessions.value.map((session) => ({
      session_id: session.id,
      workspace_id: input.currentWorkspace.value?.workspace_id ?? record.workspace_id,
      role: session.role,
      title: session.title,
      run_id: session.runId,
      created_at: '',
    }));
    const next = upsertTerminalSession(existingRecords, record);
    input.terminalSessions.value = next.map((session) => mapTerminalSessionRecord(session));
    input.activeTerminalSessionId.value = record.session_id;
  }

  async function createTerminalSession(options: {
    role?: 'operator' | 'agent';
    title?: string;
  } = {}): Promise<TerminalSessionRecord | null> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return null;
    }

    const role = options.role ?? 'operator';
    const title = options.title ?? (role === 'agent' ? 'vaxon' : 'bash');
    const created = await createWorkspaceTerminalSession(workspaceId, {
      role,
      title,
    });
    applyTerminalSession(created);
    input.revealIdeTerminalPanel();
    return created;
  }

  async function createVaxonTerminalSession(runId?: string | null): Promise<void> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    const existing = input.terminalSessions.value.find(
      (session) =>
        session.role === 'agent' &&
        (session.title === 'vaxon' || /^agent/i.test(session.title)),
    );
    if (existing) {
      input.activeTerminalSessionId.value = existing.id;
      input.revealIdeTerminalPanel();
      return;
    }
    const created = await createWorkspaceTerminalSession(workspaceId, {
      role: 'agent',
      title: 'vaxon',
      runId: runId ?? input.ideAgentRunId.value ?? null,
    });
    applyTerminalSession(created);
    input.revealIdeTerminalPanel();
  }

  async function backgroundIdeAgentRun(): Promise<void> {
    armAgentShellMirror();
    input.revealIdeTerminalPanel();
    const agentSession = input.terminalSessions.value.find((session) => session.role === 'agent');
    if (agentSession) {
      input.activeTerminalSessionId.value = agentSession.id;
      return;
    }
    await createVaxonTerminalSession(input.ideAgentRunId.value);
  }

  async function runCommandInOperatorTerminal(command: string): Promise<void> {
    const trimmed = command.trim();
    if (!trimmed) {
      return;
    }
    queueOperatorTerminalCommand(trimmed);
    input.revealIdeTerminalPanel();
    const operatorSession = input.terminalSessions.value.find(
      (session) => session.role === 'operator',
    );
    if (operatorSession) {
      input.activeTerminalSessionId.value = operatorSession.id;
      return;
    }
    await createTerminalSession({ role: 'operator', title: 'bash' });
  }

  async function splitTerminalSession(sessionId: string): Promise<string | null> {
    const source = input.terminalSessions.value.find((session) => session.id === sessionId);
    if (!source) {
      return null;
    }
    const created = await createTerminalSession({
      role: 'operator',
      title: source.role === 'agent' ? 'bash' : source.title || 'bash',
    });
    return created?.session_id ?? null;
  }

  async function renameTerminalSession(sessionId: string, nextTitle: string): Promise<void> {
    const title = nextTitle.trim();
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!title || !workspaceId) {
      return;
    }
    const updated = await renameWorkspaceTerminalSession(workspaceId, sessionId, title);
    applyTerminalSession(updated);
  }

  async function closeTerminalSession(sessionId: string): Promise<void> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return;
    }
    try {
      const snapshot = await deleteWorkspaceTerminalSession(workspaceId, sessionId);
      const mapped = snapshot.items.map((item) => mapTerminalSessionRecord(item));
      input.terminalSessions.value = mapped.length ? mapped : [...DEFAULT_TERMINAL_SESSIONS];
      if (!input.terminalSessions.value.some((session) => session.id === input.activeTerminalSessionId.value)) {
        input.activeTerminalSessionId.value =
          input.terminalSessions.value[0]?.id ?? DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
      }
    } catch {
      if (sessionId === DEFAULT_OPERATOR_TERMINAL_SESSION_ID) {
        input.terminalSessions.value = [...DEFAULT_TERMINAL_SESSIONS];
        input.activeTerminalSessionId.value = DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
      } else {
        const remaining = input.terminalSessions.value.filter((session) => session.id !== sessionId);
        input.terminalSessions.value = remaining.length ? remaining : [...DEFAULT_TERMINAL_SESSIONS];
        if (!input.terminalSessions.value.some((session) => session.id === input.activeTerminalSessionId.value)) {
          input.activeTerminalSessionId.value =
            input.terminalSessions.value[0]?.id ?? DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
        }
      }
    }
    input.revealIdeTerminalPanel();
  }

  return {
    activeTerminalSession,
    applyAgentTerminalSession: applyTerminalSession,
    backgroundIdeAgentRun,
    closeTerminalSession,
    createTerminalSession,
    createVaxonTerminalSession,
    loadTerminalSessions,
    renameTerminalSession,
    runCommandInOperatorTerminal,
    setActiveTerminalSession,
    splitTerminalSession,
    terminalSessions: input.terminalSessions,
  };
}
