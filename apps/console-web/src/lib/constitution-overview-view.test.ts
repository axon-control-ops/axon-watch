import { describe, expect, it } from 'vitest';

import {
  buildConstitutionCountCards,
  buildConstitutionListCards,
} from './constitution-overview-view';
import type { ConstitutionConsoleSnapshot } from '../api/constitution-api';

function snapshot(): ConstitutionConsoleSnapshot {
  return {
    overview: {
      status: 'available',
      source_of_truth: 'AXON-X Engineering Constitution',
      registries: {
        evidence_registry: 3,
        mission_registry: 1,
        decision_registry: 2,
        capability_registry: 4,
        adr_registry: 5,
        technical_debt_registry: 6,
        platform_health_registry: 7,
      },
    },
    missions: { count: 1, items: [{ mission_id: 'mission-1', workspace_id: 'w', title: 'Fix agents', status: 'active', risk: 'normal' }] },
    decisions: { count: 1, items: [{ decision_id: 'decision-1', actor: 'Dana', decision: 'dispatch', tier: 'auto_safe', risk: 'normal' }] },
    capabilities: { count: 1, items: [{ capability_id: 'CAP-034', name: 'Autonomous Attention Loop', status: 'active' }] },
    adrs: { count: 1, items: [{ adr_id: 'ADR-009', number: 9, title: 'Constitution Registry', status: 'accepted' }] },
    debt: { count: 1, items: [{ debt_id: 'debt-1', title: 'Missing seed data', severity: 'medium', area: 'constitution', status: 'open' }] },
    health: { count: 1, items: [{ snapshot_id: 'health-1', scope: 'platform', status: 'ready', source: 'runtime_summary' }] },
    evidence: { count: 0, items: [] },
  };
}

describe('constitution overview view', () => {
  it('builds stable count cards from registry totals', () => {
    expect(buildConstitutionCountCards(snapshot())).toEqual([
      { id: 'evidence_registry', label: 'Evidence', value: 3 },
      { id: 'mission_registry', label: 'Missions', value: 1 },
      { id: 'decision_registry', label: 'Decisions', value: 2 },
      { id: 'capability_registry', label: 'Capabilities', value: 4 },
      { id: 'adr_registry', label: 'ADRs', value: 5 },
      { id: 'technical_debt_registry', label: 'Debt', value: 6 },
      { id: 'platform_health_registry', label: 'Health', value: 7 },
    ]);
  });

  it('renders human-readable summaries for the operator', () => {
    const cards = buildConstitutionListCards(snapshot());

    expect(cards[0].items[0]).toBe('Fix agents · active · normal');
    expect(cards[1].items[0]).toBe('Dana: dispatch · auto_safe');
    expect(cards[3].items[0]).toBe('ADR-009 · Constitution Registry · accepted');
  });
});
