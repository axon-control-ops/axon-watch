import { describe, expect, it } from 'vitest';

import { shouldSoftRouteToTeammate } from './composer-teammate-route';

const dashproRoster = [
  {
    employee_id: 'employee-workspace_dashpro-lead-0',
    name: 'Dana',
    role: 'lead',
    role_label: 'Lead',
    owns: 'DashPro product priorities, CI triage decisions, and handoffs',
  },
  {
    employee_id: 'employee-workspace_dashpro-watcher-1',
    name: 'Cass',
    role: 'watcher',
    role_label: 'Watcher',
    owns: 'DashPro signals, runtime health, and CI red-build alerts',
  },
  {
    employee_id: 'employee-workspace_dashpro-frontend-2',
    name: 'Priya',
    role: 'frontend',
    role_label: 'Frontend',
    owns: 'DashPro UI/UX and Expo/Android app-config CI breaks',
  },
  {
    employee_id: 'employee-workspace_dashpro-backend-3',
    name: 'Marco',
    role: 'backend',
    role_label: 'Backend',
    owns: 'DashPro APIs, services, and quality-gate CI failures',
  },
  {
    employee_id: 'employee-workspace_dashpro-integrations-4',
    name: 'Soren',
    role: 'integrations',
    role_label: 'Integrations',
    owns: 'DashPro connectors, GitHub Actions, runner/SDK/secrets CI wiring',
  },
] as const;

const marco = dashproRoster[3];
const priya = dashproRoster[2];

describe('composer-teammate-route', () => {
  it('routes enrollment confirmation UI work from Marco to Priya', () => {
    const decision = shouldSoftRouteToTeammate(
      "It's still not working — child enrollment confirmation is missing on the canary build for Marrion's account, no popup or card.",
      marco,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(true);
    expect(decision.employee?.name).toBe('Priya');
    expect(decision.fromName).toBe('Marco');
    expect(decision.reason).toBe('role_frontend');
  });

  it('routes API quality-gate work from Priya to Marco', () => {
    const decision = shouldSoftRouteToTeammate(
      'Fix the quality-gate failure on /api/enrollment and the supabase rpc.',
      priya,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(true);
    expect(decision.employee?.name).toBe('Marco');
    expect(decision.reason).toBe('role_backend');
  });

  it('does not route an ambiguous canary-only prompt', () => {
    const decision = shouldSoftRouteToTeammate('check canary', marco, dashproRoster);
    expect(decision.shouldRoute).toBe(false);
  });

  it('does not route when already on the owning teammate', () => {
    const decision = shouldSoftRouteToTeammate(
      'The enrollment confirmation popup is missing on the Expo screen.',
      priya,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('already_owning');
  });

  it('does not route without an active employee thread', () => {
    const decision = shouldSoftRouteToTeammate(
      'Fix the enrollment confirmation UI card.',
      null,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('no_active_employee');
  });
});
