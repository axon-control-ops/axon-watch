import { describe, expect, it } from 'vitest';

import {
  employeeDeliveryDetailTooltip,
  humanizeEmployeeDeliveryHandoff,
  resolveEmployeeDeliveryLinks,
} from './employee-delivery-handoff-view';

describe('humanizeEmployeeDeliveryHandoff', () => {
  it('turns raw CI-green delivery fields into plain English', () => {
    const line = humanizeEmployeeDeliveryHandoff({
      stage: 'ci_green',
      detail:
        'worker/run_ef9e6040ce5f · https://github.com/axon-control-ops/dashpro/pull/15 · SUCCESS',
      draftPrUrl: 'https://github.com/axon-control-ops/dashpro/pull/15',
      ciStatus: 'SUCCESS',
    });
    expect(line).toBe(
      'Latest handoff: CI checks passed, and draft pull request #15 is ready.',
    );
    expect(line).not.toMatch(/worker\/run_|https?:\/\//i);
  });

  it('humanizes the screenshot-style Delivery beat without structured fields', () => {
    const line = humanizeEmployeeDeliveryHandoff({
      stage: 'ci green',
      detail:
        'worker/run_ef9e6040ce5f - `https://github.com/axon-control-ops/dashpro/pull/15` - SUCCESS',
    });
    expect(line).toMatch(/CI checks passed/i);
    expect(line).toMatch(/pull request #15/i);
    expect(line).not.toContain('worker/run_');
  });

  it('reports CI failure plainly', () => {
    expect(
      humanizeEmployeeDeliveryHandoff({
        stage: 'ci_failed',
        ciStatus: 'failure',
      }),
    ).toBe('Latest handoff: CI checks failed.');
  });

  it('says checks are running on the open PR while CI is pending', () => {
    expect(
      humanizeEmployeeDeliveryHandoff({
        stage: 'ci_pending',
        detail:
          'worker/run_e6476dedf70c · https://github.com/axon-control-ops/dashpro/pull/16 · pending',
        draftPrUrl: 'https://github.com/axon-control-ops/dashpro/pull/16',
        ciStatus: 'pending',
      }),
    ).toBe('Latest handoff: Checks are still running on draft pull request #16.');
  });
});

describe('resolveEmployeeDeliveryLinks', () => {
  it('exposes open PR and CI URLs while checks run', () => {
    expect(
      resolveEmployeeDeliveryLinks({
        stage: 'ci_pending',
        draftPrUrl: 'https://github.com/axon-control-ops/dashpro/pull/16',
        ciRunUrl: 'https://github.com/axon-control-ops/dashpro/actions/runs/1',
        ciStatus: 'pending',
      }),
    ).toEqual({
      draftPrUrl: 'https://github.com/axon-control-ops/dashpro/pull/16',
      ciRunUrl: 'https://github.com/axon-control-ops/dashpro/actions/runs/1',
      prNumber: '16',
      running: true,
    });
  });

  it('falls back to the PR checks tab when the Actions run URL is missing', () => {
    expect(
      resolveEmployeeDeliveryLinks({
        stage: 'ci_pending',
        draftPrUrl: 'https://github.com/axon-control-ops/dashpro/pull/16',
        ciStatus: 'pending',
      })?.ciRunUrl,
    ).toBe('https://github.com/axon-control-ops/dashpro/pull/16/checks');
  });
});

describe('employeeDeliveryDetailTooltip', () => {
  it('keeps the technical receipt for hover', () => {
    expect(
      employeeDeliveryDetailTooltip({
        stage: 'ci_green',
        detail: 'worker/run_abc',
        draftPrUrl: 'https://github.com/org/repo/pull/2',
        ciStatus: 'SUCCESS',
      }),
    ).toContain('ci_green');
  });
});
