import { describe, expect, it } from 'vitest';

import routeCases from '../../../../packages/shared-types/fixtures/teammate-route-cases.json';
import {
  isAmbiguousTeammateRoute,
  shouldSoftRouteToTeammate,
  type TeammateRouteEmployee,
} from './composer-teammate-route';

const dashproRoster = routeCases.roster satisfies TeammateRouteEmployee[];

describe('composer-teammate-route', () => {
  for (const routeCase of routeCases.cases) {
    it(`matches golden case: ${routeCase.id}`, () => {
      const current = routeCase.current_employee_id
        ? dashproRoster.find(
            (employee) => employee.employee_id === routeCase.current_employee_id,
          )
        : null;
      const decision = shouldSoftRouteToTeammate(
        routeCase.prompt,
        current,
        dashproRoster,
      );
      expect(decision.shouldRoute).toBe(routeCase.should_route);
      expect(decision.reason).toBe(routeCase.reason);
      if (routeCase.employee_id) {
        expect(decision.employee?.employee_id).toBe(routeCase.employee_id);
      }
    });
  }

  it('preserves source and previous teammate metadata', () => {
    const marco = dashproRoster[3];
    const decision = shouldSoftRouteToTeammate(
      "It's still not working — child enrollment confirmation is missing on the canary build for Marrion's account, no popup or card.",
      marco,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(true);
    expect(decision.employee?.name).toBe('Priya');
    expect(decision.fromName).toBe('Marco');
    expect(decision.reason).toBe('role_frontend');
    expect(decision.source).toBe('deterministic');
  });

  it('flags near-threshold deterministic results for model tie-break', () => {
    const decision = shouldSoftRouteToTeammate(
      'Fix the workflow',
      dashproRoster[3],
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.ambiguous).toBe(true);
    expect(isAmbiguousTeammateRoute(decision)).toBe(true);
  });

  it('keeps multi-role Lead dispatch prompts on Dana', () => {
    const dana = dashproRoster[0];
    const decision = shouldSoftRouteToTeammate(
      'The three tasks from this morning are still open — task-ec42c713997048aa, task-c3f1c233ea184ade, and task-138a5dec16bf4ddf — they were never dispatched. Assign the two UI tasks to Priya (frontend) and the teacher query task to the backend specialist now. Use materialize_lead_fan_out with create_runs=True or directly lease those tasks and create queued runs.',
      dana,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('lead_fan_out');
  });

  it('does not named-route multi-role fan-out when active employee is not hydrated', () => {
    const decision = shouldSoftRouteToTeammate(
      'The three tasks from this morning are still open — task-ec42c713997048aa, task-c3f1c233ea184ade, and task-138a5dec16bf4ddf — they were never dispatched. Assign the two UI tasks to Priya (frontend) and the teacher query task to the backend specialist now. Use materialize_lead_fan_out with create_runs=True or directly lease those tasks and create queued runs.',
      null,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('lead_fan_out');
  });

  it('keeps a staged MoveIT unblock brief on Jabulani', () => {
    const roster: TeammateRouteEmployee[] = [
      {
        employee_id: 'moveit-lead',
        name: 'Jabulani',
        role: 'lead',
        role_label: 'Lead',
        owns: 'priorities and handoffs',
      },
      {
        employee_id: 'moveit-watcher',
        name: 'Remy',
        role: 'watcher',
        role_label: 'Watcher',
        owns: 'verification',
      },
      {
        employee_id: 'moveit-frontend',
        name: 'Ayesha',
        role: 'frontend',
        role_label: 'Frontend',
        owns: 'UI/UX',
      },
      {
        employee_id: 'moveit-backend',
        name: 'Reed',
        role: 'backend',
        role_label: 'Backend',
        owns: 'APIs',
      },
    ];
    const decision = shouldSoftRouteToTeammate(
      `Ayesha's planning is complete. Do NOT send her another planning task.
Jabulani's immediate responsibility:
1. Diagnose why the MoveIT workspace delivery route is missing.
2. Fix the smallest control-plane/configuration issue.
3. Only after delivery is confirmed, assign Reed the minimum contracts.
4. Then assign Ayesha Customer Home and Job Confirmation.
5. Remy verifies the complete first slice.`,
      roster[0],
      roster,
    );

    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('lead_fan_out');
    expect(decision.fromName).toBe('Jabulani');
  });

  it('does not switch teammates for pronoun-only named assigns', () => {
    const dana = dashproRoster[0];
    const decision = shouldSoftRouteToTeammate(
      'Route the task to Priya',
      dana,
      dashproRoster,
    );
    expect(decision.shouldRoute).toBe(false);
    expect(decision.reason).toBe('vague_named_assign');
    expect(decision.employee?.name).toBe('Priya');
  });

  it('does not spend a model call on a zero-signal prompt', () => {
    const decision = shouldSoftRouteToTeammate(
      'check canary',
      dashproRoster[3],
      dashproRoster,
    );
    expect(decision.winnerScore).toBe(0);
    expect(isAmbiguousTeammateRoute(decision)).toBe(false);
  });
});
