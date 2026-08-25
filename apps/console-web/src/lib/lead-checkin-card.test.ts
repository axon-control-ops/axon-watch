import { describe, expect, it } from 'vitest';

import {
  humanizeLeadFailureDetail,
  looksLikeLeadCheckinReport,
  parseLeadCheckinReport,
} from './lead-checkin-card';
import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

const SAMPLE = [
  'Lead check-in: scheduled team health pass.',
  'Findings: 1 · Assignments created: 0',
  '',
  '1. [failed_shift] Priya (frontend) last shift failed (→ frontend)',
  '   Lane B finalization failed: review_ready/complete blocked: acceptance_evidence did not pass [Gate 6] | acceptance=fail - policy=out_of_scope - mode=contract - paths=22 - .. [run=run_5e4855fc6e75]',
].join('\n');

describe('lead-checkin-card', () => {
  it('detects the deterministic Lead check-in dump', () => {
    expect(looksLikeLeadCheckinReport(SAMPLE)).toBe(true);
    expect(looksLikeLeadCheckinReport('Here is a normal reply.')).toBe(false);
  });

  it('humanizes Gate 6 / out-of-scope dumps', () => {
    expect(
      humanizeLeadFailureDetail(
        'Lane B finalization failed: acceptance_evidence did not pass [Gate 6] | policy=out_of_scope',
      ),
    ).toMatch(/out of scope/i);
  });

  it('parses findings, next steps, and options', () => {
    const card = parseLeadCheckinReport(SAMPLE);
    expect(card).not.toBeNull();
    expect(card?.findingCount).toBe(1);
    expect(card?.assignmentCount).toBe(0);
    expect(card?.findings[0]?.title).toContain('Priya');
    expect(card?.findings[0]?.detail).toMatch(/acceptance/i);
    expect(card?.nextSteps[0]).toMatch(/Priya/i);
    expect(card?.options.some((option) => /Retry Priya/i.test(option.label))).toBe(true);
    expect(card?.options.some((option) => /Recovery Center/i.test(option.label))).toBe(true);
  });

  it('upgrades check-in dumps into a dedicated transcript card', () => {
    expect(parseAgentTranscriptBlocks(SAMPLE).map((segment) => segment.kind)).toEqual([
      'lead-checkin',
    ]);
  });

  it('does not make an all-clear health pass into a decision card', () => {
    const clear = parseLeadCheckinReport(
      ['Lead check-in: scheduled team health pass.', 'Findings: 0 · Assignments created: 0'].join('\n'),
    );
    expect(clear?.options).toEqual([]);
  });

  it('renders a blocked card with no invented options menu (the reported bug)', () => {
    const decisionPayload = {
      card_type: 'blocked',
      summary: "Workspace delivery isn't configured for workspace_moveit.",
      classification: 'missing_workspace_delivery_config',
      operator_action_required: true,
      recommended_action: 'Enable a workspace delivery policy for workspace_moveit.',
      automatic_next_action: null,
      actions_attempted: ['Inspected the failed run', 'Checked the live workspace delivery policy'],
      evidence: [{ label: 'Failed run', ref: 'run_eb27cfd30ee4' }],
      confidence: 0.95,
      retry_eligible: false,
      recovery_eligible: false,
      escalation_reason: 'Workspace delivery policy is a host/operator-level configuration.',
      choices: [],
    };
    const sample = [
      'Lead check-in: scheduled team health pass.',
      'Findings: 1 · Assignments created: 0',
      '',
      '1. [operator_blocker] Jabulani (lead) last shift failed (ESCALATE)',
      '   Workspace delivery blocked: workspace delivery is not configured for MoveIT',
      ':::decision',
      JSON.stringify(decisionPayload),
      ':::',
    ].join('\n');

    const card = parseLeadCheckinReport(sample);
    expect(card).not.toBeNull();
    expect(card?.findings[0]?.decision?.cardType).toBe('blocked');
    expect(card?.findings[0]?.decision?.choices).toEqual([]);
    // The whole point of the fix: no "Fix / Inspect / Recovery Center / Hold" menu.
    expect(card?.options).toEqual([]);
    expect(card?.nextSteps[0]).toContain('Enable a workspace delivery policy');
  });

  it('renders a decision_required card with the actual backend-authored choices', () => {
    const decisionPayload = {
      card_type: 'decision_required',
      summary: 'Two workspaces both need the same fix; pick which to prioritize.',
      classification: 'ambiguous_business_choice',
      operator_action_required: true,
      recommended_action: 'Fix workspace_dashpro first.',
      automatic_next_action: null,
      actions_attempted: [],
      evidence: [],
      confidence: 0.4,
      retry_eligible: false,
      recovery_eligible: false,
      escalation_reason: null,
      choices: [
        {
          id: '1',
          label: 'Fix workspace_dashpro first',
          expected_result: "dashpro's pipeline is corrected this shift",
          risk: 'workspace_tps stays blocked a bit longer',
          recommended: true,
          is_pause: false,
        },
        {
          id: '2',
          label: 'Pause and review later',
          expected_result: 'No change is made until you decide',
          risk: 'Both workspaces remain blocked',
          recommended: false,
          is_pause: true,
        },
      ],
    };
    const sample = [
      'Lead check-in: scheduled team health pass.',
      'Findings: 1 · Assignments created: 0',
      '',
      '1. [operator_blocker] Priya (lead) last shift failed (ESCALATE)',
      '   Ambiguous business choice between two workspaces.',
      ':::decision',
      JSON.stringify(decisionPayload),
      ':::',
    ].join('\n');

    const card = parseLeadCheckinReport(sample);
    expect(card?.options).toHaveLength(2);
    expect(card?.options[0]?.label).toBe('Fix workspace_dashpro first');
    expect(card?.prompt).toBe(decisionPayload.summary);
  });

  it('falls back to legacy options when the fence body is malformed JSON', () => {
    const sample = [
      'Lead check-in: scheduled team health pass.',
      'Findings: 1 · Assignments created: 0',
      '',
      '1. [failed_shift] Priya (frontend) last shift failed (→ frontend)',
      '   Some detail.',
      ':::decision',
      '{not valid json',
      ':::',
    ].join('\n');

    const card = parseLeadCheckinReport(sample);
    expect(card?.findings[0]?.decision).toBeUndefined();
    expect(card?.options.length).toBeGreaterThan(0);
  });
});
