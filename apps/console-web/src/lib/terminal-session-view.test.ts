import { describe, expect, it } from 'vitest';

import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
  sortTerminalSessionsOperatorFirst,
  terminalSessionTabLabel,
  upsertTerminalSession,
  type TerminalSessionRecord,
} from './terminal-session-view';

describe('terminal session view', () => {
  it('labels agent sessions distinctly', () => {
    const session: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'Agent shell',
      run_id: 'run_abc',
      created_at: '2026-07-07T12:00:00Z',
    };

    expect(terminalSessionTabLabel(session)).toBe('Agent shell');
  });

  it('keeps the operator session first', () => {
    const operator: TerminalSessionRecord = {
      session_id: DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
      workspace_id: 'workspace_axon_watch',
      role: 'operator',
      title: 'Terminal',
      run_id: null,
      created_at: '2026-07-07T10:00:00Z',
    };
    const agent: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'Agent shell',
      run_id: 'run_abc',
      created_at: '2026-07-07T12:00:00Z',
    };

    expect(
      sortTerminalSessionsOperatorFirst([agent, operator]).map((item) => item.session_id),
    ).toEqual([DEFAULT_OPERATOR_TERMINAL_SESSION_ID, 'terminal-agent-abc']);
  });

  it('upserts sessions by id', () => {
    const existing: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'Old title',
      run_id: 'run_abc',
      created_at: '2026-07-07T12:00:00Z',
    };
    const updated: TerminalSessionRecord = {
      ...existing,
      title: 'Agent shell',
    };

    expect(upsertTerminalSession([existing], updated)[0]?.title).toBe('Agent shell');
  });
});
