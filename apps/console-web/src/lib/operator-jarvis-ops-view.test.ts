import { describe, expect, it } from 'vitest';

import { buildJarvisOpsView } from './operator-jarvis-ops-view';

describe('buildJarvisOpsView', () => {
  it('surfaces run, poll, and agent cards', () => {
    const view = buildJarvisOpsView({
      briefing: null,
      primaryActiveRun: {
        run_id: 'run_abc',
        summary: 'OTA monitor',
        detail: 'Polling terminal',
        phase: 'executing',
        status: 'running',
        current_step: 'Await shell output',
      },
      fleetActiveRuns: [],
      ideComposerActivity: {
        label: 'Full Access — streaming runtime output…',
        mode: 'agent',
        executionAccess: 'full',
        liveBodyFull: 'Polling the terminal file to check for completion.',
      },
      employees: [
        {
          employee_id: 'emp_dana',
          workspace_id: 'ws_dash',
          name: 'Dana',
          role: 'lead',
          role_label: 'Lead',
          schedule: 'always_on',
          schedule_label: 'Always on',
          status: 'executing',
          owns: 'OTA handoff',
          enabled: true,
          primary: true,
        },
      ],
      agentStreamActive: true,
    });

    expect(view.cards.some((card) => card.kind === 'run')).toBe(true);
    expect(view.cards.some((card) => card.kind === 'poll')).toBe(true);
    expect(view.cards.some((card) => card.kind === 'agent' && card.title === 'Dana')).toBe(true);
  });

  it('surfaces VAXON tasks without partial-word truncation', () => {
    const view = buildJarvisOpsView({
      briefing: null,
      primaryActiveRun: null,
      fleetActiveRuns: [],
      ideComposerActivity: null,
      employees: [],
      agentStreamActive: false,
      workspaceNamesById: { workspace_young_eagles: 'Young Eagles' },
      workspaceTasks: [{
        task_id: 'task-1', workspace_id: 'workspace_young_eagles',
        goal: `${'Complete parent graduation confirmation verification '.repeat(6)}cleanly`,
        acceptance_criteria: '', risk: 'normal', owner_role: 'lead', dependencies: [],
        status: 'leased', lease_holder: 'employee-imani', lease_expires_at: null,
        attempt_budget: 3, attempts_used: 1, terminal_outcome: null, run_id: 'run-1',
        created_at: '2026-08-04T05:00:00Z', updated_at: '2026-08-04T05:01:00Z',
      }],
    });

    const task = view.cards.find((card) => card.kind === 'task');
    expect(task?.title).toBe('VAXON · lead');
    expect(task?.meta).toContain('working · Young Eagles');
    expect(task?.detail).toMatch(/\bparent…$/);
    expect(task?.detail).not.toContain('confirmati…');
  });
});
