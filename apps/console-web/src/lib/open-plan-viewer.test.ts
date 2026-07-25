import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/plans-api', () => ({
  fetchPlan: vi.fn(),
}));

import { fetchPlan } from '../api/plans-api';
import { openPlanInEditor } from './open-plan-viewer';

describe('openPlanInEditor', () => {
  beforeEach(() => {
    vi.mocked(fetchPlan).mockReset();
  });

  it('opens fetched plan content in the editor with preview preference', async () => {
    vi.mocked(fetchPlan).mockResolvedValue({
      plan_id: 'plan_abcdef123456',
      workspace_id: 'workspace_alpha',
      thread_id: 'thread_1',
      source_message_id: 'message_1',
      title: 'Soft cutover',
      path: '/tmp/.axon/plans/plan_abcdef123456.md',
      created_at: '2026-07-15T00:00:00Z',
      updated_at: '2026-07-15T00:00:00Z',
      content: '# Soft cutover\n\n1. Proxy\n',
    });
    const openAgentContentInEditor = vi.fn(() => 'draft:plan-1');
    const opened = await openPlanInEditor({
      shell: { openAgentContentInEditor },
      workspaceId: 'workspace_alpha',
      planId: 'plan_abcdef123456',
    });
    expect(opened).toBe('draft:plan-1');
    expect(openAgentContentInEditor).toHaveBeenCalledWith({
      title: 'Plan · Soft cutover',
      content: '# Soft cutover\n\n1. Proxy',
      preferPreview: true,
      focus: true,
      readOnly: true,
      planId: 'plan_abcdef123456',
    });
  });

  it('sanitizes weak plan titles in the editor tab label', async () => {
    vi.mocked(fetchPlan).mockResolvedValue({
      plan_id: 'plan_abcdef123456',
      workspace_id: 'workspace_alpha',
      thread_id: 'thread_1',
      source_message_id: 'message_1',
      title: "I'll look through the repo for the mobile control plan",
      path: '/tmp/.axon/plans/plan_abcdef123456.md',
      created_at: '2026-07-15T00:00:00Z',
      updated_at: '2026-07-15T00:00:00Z',
      content: '# Soft cutover\n\n1. Proxy\n',
    });
    const openAgentContentInEditor = vi.fn(() => 'draft:plan-1');
    await openPlanInEditor({
      shell: { openAgentContentInEditor },
      workspaceId: 'workspace_alpha',
      planId: 'plan_abcdef123456',
    });
    expect(openAgentContentInEditor).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Plan · Plan',
      }),
    );
  });
});
