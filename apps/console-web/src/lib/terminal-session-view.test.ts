import { describe, expect, it } from 'vitest';

import {
  DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
  DEFAULT_VAXON_TERMINAL_TITLE,
  sortTerminalSessionsOperatorFirst,
  terminalSessionBranchBadge,
  terminalSessionRootTitle,
  terminalSessionTabLabel,
  type TerminalSessionRecord,
  upsertTerminalSession,
} from './terminal-session-view';

describe('terminal session view', () => {
  it('labels legacy agent shells as vaxon', () => {
    const session: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'Agent shell',
      run_id: 'run_abc',
      created_at: '2026-07-07T12:00:00Z',
    };

    expect(terminalSessionTabLabel(session)).toBe(DEFAULT_VAXON_TERMINAL_TITLE);
  });

  it('keeps explicit vaxon titles marked as agent', () => {
    const session: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'vaxon',
      run_id: 'run_abc',
      created_at: '2026-07-07T12:00:00Z',
    };

    expect(terminalSessionTabLabel(session)).toBe('vaxon · agent');
  });

  it('labels generic operator Terminal tabs as local zsh', () => {
    const session: TerminalSessionRecord = {
      session_id: DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
      workspace_id: 'workspace_axon_watch',
      role: 'operator',
      title: 'Terminal',
      run_id: null,
      created_at: '2026-07-07T10:00:00Z',
    };

    expect(terminalSessionTabLabel(session)).toBe('zsh · local');
  });

  it('labels zsh operator tabs as local', () => {
    const session: TerminalSessionRecord = {
      session_id: DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
      workspace_id: 'workspace_axon_watch',
      role: 'operator',
      title: 'zsh',
      run_id: null,
      created_at: '2026-07-07T10:00:00Z',
    };

    expect(terminalSessionTabLabel(session)).toBe('zsh · local');
  });

  it('keeps the operator session first', () => {
    const operator: TerminalSessionRecord = {
      session_id: DEFAULT_OPERATOR_TERMINAL_SESSION_ID,
      workspace_id: 'workspace_axon_watch',
      role: 'operator',
      title: 'bash',
      run_id: null,
      created_at: '2026-07-07T10:00:00Z',
    };
    const agent: TerminalSessionRecord = {
      session_id: 'terminal-agent-abc',
      workspace_id: 'workspace_axon_watch',
      role: 'agent',
      title: 'vaxon',
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
      title: 'vaxon',
    };

    expect(upsertTerminalSession([existing], updated)[0]?.title).toBe('vaxon');
  });
});

describe('isolated session labelling', () => {
  const base = {
    session_id: 'terminal-sandbox',
    workspace_id: 'workspace_dashpro',
    role: 'agent' as const,
    title: 'vaxon · sandbox',
    run_id: null,
    created_at: '',
  };

  it('badges an isolated lane with its own branch, not the bound branch', () => {
    expect(
      terminalSessionBranchBadge({ ...base, isolated: true, branch: 'worker/composer-x' }),
    ).toBe('worker/composer-x');
  });

  it('never badges a bound lane, even though it knows the branch', () => {
    // Showing `development` on every tab is the confusion this avoids.
    expect(
      terminalSessionBranchBadge({
        ...base,
        session_id: 'terminal-agent',
        isolated: false,
        branch: 'development',
      }),
    ).toBe('');
  });

  it('falls back to a generic marker when the branch cannot be read', () => {
    expect(terminalSessionBranchBadge({ ...base, isolated: true, branch: '' })).toBe('isolated');
  });

  it('names the checkout in the hover title so cwd is unambiguous', () => {
    const title = terminalSessionRootTitle({
      ...base,
      isolated: true,
      cwd: '/tmp/axon-si/checkout',
      branch: 'worker/composer-x',
    });
    expect(title).toContain('Sandbox checkout: /tmp/axon-si/checkout');
    expect(title).toContain('branch worker/composer-x');
  });
});
