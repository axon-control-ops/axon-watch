import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: vi.fn(),
}));

vi.mock('./ide-composer-restore-request', () => ({
  requestIdeComposerMode: vi.fn(),
}));

import type { CompanyEmployeeRecord } from '../contracts/canonical';
import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import { requestIdeComposerMode } from './ide-composer-restore-request';
import { runEmployeeShiftRetry } from './run-employee-shift-retry';

function employee(overrides: Partial<CompanyEmployeeRecord> = {}): CompanyEmployeeRecord {
  return {
    employee_id: 'e1',
    workspace_id: 'workspace_demo',
    name: 'Jules',
    role: 'frontend',
    role_label: 'UI/UX',
    schedule: 'continuous',
    schedule_label: 'Continuous',
    status: 'idle',
    owns: 'console UI/UX',
    enabled: true,
    primary: false,
    last_outcome: 'failed',
    last_outcome_detail: 'vitest assertion failed',
    ...overrides,
  };
}

describe('runEmployeeShiftRetry', () => {
  beforeEach(() => {
    vi.mocked(requestIdeComposerMode).mockReset();
    vi.mocked(focusAgentDockComposerInput).mockReset();
  });

  it('focuses the teammate thread, seeds agent full, and submits immediately', async () => {
    const openOrFocusEmployeeIdeThread = vi.fn().mockResolvedValue('thread_1');
    const openIdeComposerWithDraft = vi.fn();
    const setAgentExecutionAccess = vi.fn();
    const submitIdeComposer = vi.fn().mockResolvedValue(undefined);

    const result = await runEmployeeShiftRetry(
      {
        openOrFocusEmployeeIdeThread,
        openIdeComposerWithDraft,
        setAgentExecutionAccess,
        submitIdeComposer,
      },
      employee(),
    );

    expect(result.ok).toBe(true);
    expect(openOrFocusEmployeeIdeThread).toHaveBeenCalledOnce();
    expect(requestIdeComposerMode).toHaveBeenCalledWith('agent');
    expect(setAgentExecutionAccess).toHaveBeenCalledWith('full');
    expect(openIdeComposerWithDraft).toHaveBeenCalledOnce();
    const draft = vi.mocked(openIdeComposerWithDraft).mock.calls[0]?.[0] ?? '';
    expect(draft).toMatch(/my last continuous shift/i);
    expect(draft).toContain('vitest assertion failed');
    expect(focusAgentDockComposerInput).toHaveBeenCalledOnce();
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
  });

  it('can skip thread focus when the caller already focused the teammate', async () => {
    const openOrFocusEmployeeIdeThread = vi.fn().mockResolvedValue('thread_1');
    const submitIdeComposer = vi.fn().mockResolvedValue(undefined);

    await runEmployeeShiftRetry(
      {
        openOrFocusEmployeeIdeThread,
        openIdeComposerWithDraft: vi.fn(),
        setAgentExecutionAccess: vi.fn(),
        submitIdeComposer,
      },
      employee(),
      { focusThread: false },
    );

    expect(openOrFocusEmployeeIdeThread).not.toHaveBeenCalled();
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
  });
});
