import { computed, ref, type Ref } from 'vue';

import {
  createWorkspaceTerminalSession,
  deleteWorkspaceTerminalSession,
  enqueueWorkspaceAgentTerminalJob,
  fetchAgentTerminalJobStatus,
  fetchWorkspaceTerminalSessions,
  renameWorkspaceTerminalSession,
  type TerminalSessionRecord,
} from '../api/control-plane';
import {
  armAgentShellMirror,
  clearAgentShellMirrorForcedText,
  queueAgentBackgroundCommand,
  queueOperatorTerminalCommand,
} from './agent-shell-mirror-state';
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
    title: 'zsh',
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

const AGENT_TERMINAL_JOB_POLL_INTERVAL_MS = 4000;
const AGENT_TERMINAL_JOB_POLL_MAX_ATTEMPTS = 90; // ~6 minutes

const TERMINAL_JOB_STATUSES_TERMINAL = new Set(['completed', 'failed', 'error', 'cancelled']);

export function createTerminalSessionStore(input: TerminalSessionStoreInput) {
  const activeTerminalSession = computed(
    () =>
      input.terminalSessions.value.find((session) => session.id === input.activeTerminalSessionId.value) ??
      DEFAULT_TERMINAL_SESSIONS[0],
  );

  /** job_id -> last known server-tracked status, independent of whatever the
   * terminal output stream shows (that stream can drop — see create-xterm-session
   * reconnect logic — leaving output-based status parsing stuck forever). */
  const agentTerminalJobStatuses = ref<Record<string, string>>({});

  function pollAgentTerminalJobStatus(workspaceId: string, jobId: string): void {
    let attempts = 0;
    const tick = async (): Promise<void> => {
      attempts += 1;
      try {
        const record = await fetchAgentTerminalJobStatus(workspaceId, jobId);
        agentTerminalJobStatuses.value = { ...agentTerminalJobStatuses.value, [jobId]: record.status };
        if (TERMINAL_JOB_STATUSES_TERMINAL.has(record.status)) {
          return;
        }
      } catch {
        // Transient poll failure — keep trying until max attempts; the job's
        // last known status (or "running" default) stays as-is meanwhile.
      }
      if (attempts >= AGENT_TERMINAL_JOB_POLL_MAX_ATTEMPTS) {
        agentTerminalJobStatuses.value = {
          ...agentTerminalJobStatuses.value,
          [jobId]: agentTerminalJobStatuses.value[jobId] ?? 'unknown',
        };
        return;
      }
      setTimeout(() => void tick(), AGENT_TERMINAL_JOB_POLL_INTERVAL_MS);
    };
    void tick();
  }

  async function loadTerminalSessions(workspaceId: string): Promise<void> {
    try {
      const snapshot = await fetchWorkspaceTerminalSessions(workspaceId);
      const mapped = snapshot.items.map((item) => mapTerminalSessionRecord(item));
      input.terminalSessions.value = mapped.length ? mapped : [...DEFAULT_TERMINAL_SESSIONS];
      if (!input.terminalSessions.value.some((session) => session.id === input.activeTerminalSessionId.value)) {
        input.activeTerminalSessionId.value = DEFAULT_OPERATOR_TERMINAL_SESSION_ID;
      }
      // Legacy default operator tab was titled "bash" — rename so UI + PTY prefer zsh.
      const legacyBash = input.terminalSessions.value.find(
        (session) =>
          session.id === DEFAULT_OPERATOR_TERMINAL_SESSION_ID &&
          session.role === 'operator' &&
          session.title.trim().toLowerCase() === 'bash',
      );
      if (legacyBash) {
        try {
          const updated = await renameWorkspaceTerminalSession(
            workspaceId,
            legacyBash.id,
            'zsh',
          );
          applyTerminalSession(updated);
        } catch {
          /* keep bash label if rename fails; PTY still migrates after CP restart */
        }
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
    const title = options.title ?? (role === 'agent' ? 'vaxon' : 'zsh');
    try {
      const created = await createWorkspaceTerminalSession(workspaceId, {
        role,
        title,
      });
      applyTerminalSession(created);
      input.revealIdeTerminalPanel();
      return created;
    } catch (error) {
      console.error('createTerminalSession failed', error);
      return null;
    }
  }

  async function createVaxonTerminalSession(runId?: string | null): Promise<boolean> {
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!workspaceId) {
      return false;
    }
    const existing = input.terminalSessions.value.find(
      (session) =>
        session.role === 'agent' &&
        (session.title === 'vaxon' || /^agent/i.test(session.title)),
    );
    if (existing) {
      input.activeTerminalSessionId.value = existing.id;
      input.revealIdeTerminalPanel();
      return true;
    }
    try {
      const created = await createWorkspaceTerminalSession(workspaceId, {
        role: 'agent',
        title: 'vaxon',
        runId: runId ?? input.ideAgentRunId.value ?? null,
      });
      applyTerminalSession(created);
      input.revealIdeTerminalPanel();
      return true;
    } catch (error) {
      console.error('createVaxonTerminalSession failed', error);
      return false;
    }
  }

  /** Inject a command into the Axon agent PTY and focus the vaxon tab. */
  async function runCommandInAgentBackgroundTerminal(command: string): Promise<void> {
    const trimmed = command.trim();
    if (!trimmed) {
      return;
    }
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (workspaceId) {
      try {
        const job = await enqueueWorkspaceAgentTerminalJob(workspaceId, {
          command: trimmed,
          run_id: input.ideAgentRunId.value,
        });
        applyTerminalSession(job.agent_terminal_session);
        input.revealIdeTerminalPanel();
        input.activeTerminalSessionId.value = job.session_id;
        pollAgentTerminalJobStatus(workspaceId, job.job_id);
        return;
      } catch {
        // Fall through to local pending queue if control-plane is unreachable.
      }
    }
    queueAgentBackgroundCommand(trimmed);
    input.revealIdeTerminalPanel();
    const agentSession = input.terminalSessions.value.find((session) => session.role === 'agent');
    if (agentSession) {
      input.activeTerminalSessionId.value = agentSession.id;
      return;
    }
    await createVaxonTerminalSession(input.ideAgentRunId.value);
  }

  async function backgroundIdeAgentRun(command?: string | null): Promise<void> {
    // Drop any pinned snapshot so the live open `:::terminal` card can stream in.
    clearAgentShellMirrorForcedText();
    armAgentShellMirror();
    input.revealIdeTerminalPanel();
    // Do not re-run an in-flight Cursor shell command in the Axon PTY — that
    // duplicates side effects. Axon-owned jobs use runCommandInAgentBackgroundTerminal.
    void command;
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
    await createTerminalSession({ role: 'operator', title: 'zsh' });
  }

  async function splitTerminalSession(sessionId: string): Promise<string | null> {
    const source = input.terminalSessions.value.find((session) => session.id === sessionId);
    if (!source) {
      return null;
    }
    const created = await createTerminalSession({
      role: 'operator',
      title: source.role === 'agent' ? 'zsh' : source.title || 'zsh',
    });
    return created?.session_id ?? null;
  }

  async function renameTerminalSession(sessionId: string, nextTitle: string): Promise<boolean> {
    const title = nextTitle.trim();
    const workspaceId = input.currentWorkspace.value?.workspace_id;
    if (!title || !workspaceId) {
      return false;
    }
    try {
      const updated = await renameWorkspaceTerminalSession(workspaceId, sessionId, title);
      applyTerminalSession(updated);
      return true;
    } catch (error) {
      console.error('renameTerminalSession failed', error);
      return false;
    }
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
    agentTerminalJobStatuses,
    applyAgentTerminalSession: applyTerminalSession,
    backgroundIdeAgentRun,
    closeTerminalSession,
    createTerminalSession,
    createVaxonTerminalSession,
    loadTerminalSessions,
    renameTerminalSession,
    runCommandInAgentBackgroundTerminal,
    runCommandInOperatorTerminal,
    setActiveTerminalSession,
    splitTerminalSession,
    terminalSessions: input.terminalSessions,
  };
}
