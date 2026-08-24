import { describe, expect, it } from 'vitest';

import routeCases from '../../../../packages/shared-types/fixtures/teammate-route-cases.json';
import type { TeammateRouteEmployee } from './composer-teammate-route';
import {
  isVagueNamedAssignPrompt,
  matchNamedAssignEmployee,
  namedAssignActionBody,
  rewriteNamedAssignPrompt,
} from './named-assign-route';

const dashproRoster = routeCases.roster satisfies TeammateRouteEmployee[];

describe('named-assign-route', () => {
  it('matches assign/have/@ for every roster specialist', () => {
    const cases = [
      { prompt: 'Ok assign Priya the task and have her report back', name: 'Priya' },
      { prompt: 'Have Marco fix the quality-gate failure', name: 'Marco' },
      { prompt: 'Give Soren the GitHub Actions secrets wiring', name: 'Soren' },
      { prompt: '@Cass please watch the red-build alerts', name: 'Cass' },
      { prompt: 'Dispatch Dana the triage priorities', name: 'Dana' },
    ] as const;

    for (const row of cases) {
      const match = matchNamedAssignEmployee(row.prompt, dashproRoster);
      expect(match?.employee.name).toBe(row.name);
    }
  });

  it('prefers the longest name match', () => {
    const roster: TeammateRouteEmployee[] = [
      {
        employee_id: 'emp-sol',
        name: 'Sol',
        role: 'backend',
        role_label: 'Backend',
        owns: 'APIs',
      },
      {
        employee_id: 'emp-solomon',
        name: 'Solomon',
        role: 'frontend',
        role_label: 'Frontend',
        owns: 'UI',
      },
    ];
    const match = matchNamedAssignEmployee('Assign Solomon the card polish', roster);
    expect(match?.employee.employee_id).toBe('emp-solomon');
  });

  it('rewrites assign framing into an actionable specialist prompt', () => {
    const rewritten = rewriteNamedAssignPrompt(
      'Ok assign Cole the Lesego login table and have him report back',
      'Cole',
    );
    expect(rewritten).toContain('You own this assignment from Lead');
    expect(rewritten).toContain('Operator ask:');
    expect(rewritten.toLowerCase()).not.toContain('assign cole');
    expect(rewritten.toLowerCase()).toContain('lesego login table');
  });

  it('detects vague named assigns instead of inventing a handoff body', () => {
    expect(namedAssignActionBody('Route the task to Priya', 'Priya')).toBeNull();
    expect(isVagueNamedAssignPrompt('Route the task to Priya', 'Priya')).toBe(true);
    expect(rewriteNamedAssignPrompt('Route the task to Priya', 'Priya')).toContain(
      'did not include a concrete task body',
    );
  });

  it('ignores casual name mentions without assign framing', () => {
    const match = matchNamedAssignEmployee(
      'Priya already fixed the enrollment popup yesterday',
      dashproRoster,
    );
    expect(match).toBeNull();
  });
});
