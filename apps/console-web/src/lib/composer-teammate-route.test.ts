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
