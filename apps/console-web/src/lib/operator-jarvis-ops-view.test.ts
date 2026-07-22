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
});
