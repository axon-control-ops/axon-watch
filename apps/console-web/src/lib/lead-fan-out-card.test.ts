import { describe, expect, it } from 'vitest';

import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';
import {
  parseLeadFanOutFenceBody,
  tryParseLegacyLeadFanOutText,
} from './lead-fan-out-card';

describe('lead fan-out card', () => {
  it('parses the :::lead-fan-out fence body', () => {
    const card = parseLeadFanOutFenceBody(
      JSON.stringify({
        v: 1,
        plan_id: 'lead-plan-abc',
        mode: 'decompose',
        lead_name: 'Dana',
        queued: 1,
        deferred: 3,
        assignments: [
          { role: 'frontend', goal: 'Fix dashboard Payments card' },
          { role: 'backend', goal: 'Verify APIs' },
        ],
        notes: ['Fleet: 0/3 workers busy'],
      }),
      'Decomposed',
    );

    expect(card).toMatchObject({
      planId: 'lead-plan-abc',
      mode: 'decompose',
      leadName: 'Dana',
      queued: 1,
      deferred: 3,
      title: 'Decomposed',
    });
    expect(card?.assignments).toHaveLength(2);
  });

  it('parses fence segments from agent transcript', () => {
    const content = [
      'I decomposed the work and assigned specialists.',
      '',
      ':::lead-fan-out Decomposed',
      JSON.stringify({
        plan_id: 'lead-plan-e314',
        mode: 'decompose',
        lead_name: 'Dana',
        queued: 1,
        deferred: 3,
        assignments: [{ role: 'watcher', goal: 'Confirm live app health' }],
        notes: ['Continuous workers stay OFF'],
      }),
      ':::',
      '',
      '— Dana',
      '',
      'Confidence: 8/10',
    ].join('\n');

    const segments = parseAgentTranscriptBlocks(content);
    const card = segments.find((segment) => segment.kind === 'lead-fan-out');
    expect(card).toMatchObject({
      kind: 'lead-fan-out',
      planId: 'lead-plan-e314',
      leadName: 'Dana',
      queued: 1,
      deferred: 3,
    });
  });

  it('upgrades legacy plain Lead essays into a card', () => {
    const legacy = [
      'Sir King — I decomposed the work and assigned specialists (plan `lead-plan-e3144124231b4914`).',
      '',
      'Assignments:',
      '- integrations: Determine what the latest OTA update shipped for Payments.',
      '- watcher: Confirm live app health and client version.',
      '',
      'Queued runs: 1',
      '',
      'Deferred (dependencies): 3',
      '',
      'Fleet: 0/3 workers busy · up to 1 start(s) per ~45s tick.',
      'Continuous workers stay OFF (semi/manual).',
      '— Dana',
      '',
      'Confidence: 8/10',
    ].join('\n');

    const card = tryParseLegacyLeadFanOutText(legacy);
    expect(card).toMatchObject({
      planId: 'lead-plan-e3144124231b4914',
      mode: 'decompose',
      leadName: 'Dana',
      queued: 1,
      deferred: 3,
    });
    expect(card?.assignments.map((row) => row.role)).toEqual(['integrations', 'watcher']);

    const segments = parseAgentTranscriptBlocks(legacy);
    expect(segments.some((segment) => segment.kind === 'lead-fan-out')).toBe(true);
  });
});
