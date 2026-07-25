import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/plans-api', () => ({
  fetchPlan: vi.fn(),
}));

vi.mock('./agent-dock-composer-focus', () => ({
  focusAgentDockComposerInput: vi.fn(),
}));

vi.mock('./ide-composer-restore-request', () => ({
  requestIdeComposerMode: vi.fn(),
}));

import { fetchPlan } from '../api/plans-api';
import { focusAgentDockComposerInput } from './agent-dock-composer-focus';
import { buildPlan } from './build-plan-action';
import { requestIdeComposerMode } from './ide-composer-restore-request';

describe('buildPlan', () => {
  beforeEach(() => {
    vi.mocked(fetchPlan).mockReset();
    vi.mocked(requestIdeComposerMode).mockReset();
    vi.mocked(focusAgentDockComposerInput).mockReset();
  });

  it('switches to Agent Full, seeds the composer, and starts the build', async () => {
    vi.mocked(fetchPlan).mockResolvedValue({
      plan_id: 'plan_d33969250b2e',
      workspace_id: 'workspace_axon_watch',
      thread_id: 'thread_1',
      source_message_id: 'message_1',
      title: 'Mobile remote first, then employee upgrades',
      path: '/tmp/plan.md',
      created_at: '2026-07-15T00:00:00Z',
      updated_at: '2026-07-15T00:00:00Z',
      content: '# Goal\n\n1. Tunnel\n2. Shell\n3. Verify\n',
    });
    const openIdeComposerWithDraft = vi.fn();
    const setAgentExecutionAccess = vi.fn();
    const submitIdeComposer = vi.fn().mockResolvedValue(undefined);
    const result = await buildPlan(
      { openIdeComposerWithDraft, setAgentExecutionAccess, submitIdeComposer },
      {
        workspaceId: 'workspace_axon_watch',
        planId: 'plan_d33969250b2e',
      },
    );
    expect(result.ok).toBe(true);
    expect(requestIdeComposerMode).toHaveBeenCalledWith('agent');
    expect(setAgentExecutionAccess).toHaveBeenCalledWith('full');
    expect(openIdeComposerWithDraft).toHaveBeenCalledOnce();
    const prompt = vi.mocked(openIdeComposerWithDraft).mock.calls[0]?.[0] ?? '';
    expect(prompt).toContain('Build this plan (plan_d33969250b2e)');
    expect(prompt).toContain('# Goal');
    expect(focusAgentDockComposerInput).toHaveBeenCalledOnce();
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
  });

  it('uses contentOverride without refetch', async () => {
    const openIdeComposerWithDraft = vi.fn();
    const setAgentExecutionAccess = vi.fn();
    const submitIdeComposer = vi.fn().mockResolvedValue(undefined);
    const result = await buildPlan(
      { openIdeComposerWithDraft, setAgentExecutionAccess, submitIdeComposer },
      {
        workspaceId: 'workspace_axon_watch',
        planId: 'plan_d33969250b2e',
        title: 'From editor',
        contentOverride: '# From editor\n\n1. A\n2. B\n3. C\n',
      },
    );
    expect(result.ok).toBe(true);
    expect(fetchPlan).not.toHaveBeenCalled();
    expect(setAgentExecutionAccess).toHaveBeenCalledWith('full');
    expect(openIdeComposerWithDraft).toHaveBeenCalledWith(
      expect.stringContaining('# From editor'),
    );
    expect(submitIdeComposer).toHaveBeenCalledWith('agent');
  });
});
