import { describe, expect, it } from 'vitest';

import {
  buildInstructionsSpecialistContext,
  instructionsSpecialistLabel,
} from './instructions-specialist-context';
import type { CompanyEmployeeRecord, WorkspaceRecord } from '../contracts/canonical';

const workspace: WorkspaceRecord = {
  workspace_id: 'workspace_young_eagles_day_care',
  display_name: 'Young Eagles Day Care',
};

const frontendEmployee: CompanyEmployeeRecord = {
  employee_id: 'lila',
  workspace_id: workspace.workspace_id,
  name: 'Lila',
  role: 'frontend',
  role_label: 'Frontend',
  schedule: 'continuous',
  schedule_label: 'Continuous',
  status: 'idle',
  owns: 'UI and mobile screens',
  enabled: true,
  primary: false,
};

describe('instructions specialist context', () => {
  it('labels the Instructions button for the selected specialist', () => {
    expect(instructionsSpecialistLabel(frontendEmployee)).toBe(
      'Frontend instructions for Lila',
    );
    expect(instructionsSpecialistLabel(null)).toBe('detailed Markdown instructions');
  });

  it('builds the frontend request context from the selected employee and workspace', () => {
    expect(
      buildInstructionsSpecialistContext({
        workspace,
        employee: frontendEmployee,
        composerMode: 'agent',
      }),
    ).toMatchObject({
      role: 'frontend',
      agent_name: 'Lila',
      employee_id: 'lila',
      workspace_id: 'workspace_young_eagles_day_care',
      workspace_label: 'Young Eagles Day Care',
      composer_mode: 'agent',
      requested_delivery_mode: 'agent',
      owns: 'UI and mobile screens',
    });
  });

  it('does not invent a specialist when no employee tab is selected', () => {
    expect(
      buildInstructionsSpecialistContext({
        workspace,
        employee: null,
        composerMode: 'ask',
      }),
    ).toMatchObject({
      role: null,
      agent_name: null,
      employee_id: null,
      workspace_id: 'workspace_young_eagles_day_care',
      composer_mode: 'ask',
    });
  });
});
