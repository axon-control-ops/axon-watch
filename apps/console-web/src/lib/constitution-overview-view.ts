import type { ConstitutionConsoleSnapshot } from '../api/constitution-api';

export interface ConstitutionCountCard {
  id: string;
  label: string;
  value: number;
}

export interface ConstitutionListCard {
  id: string;
  label: string;
  empty: string;
  items: string[];
}

const COUNT_LABELS: Record<string, string> = {
  evidence_registry: 'Evidence',
  mission_registry: 'Missions',
  decision_registry: 'Decisions',
  capability_registry: 'Capabilities',
  adr_registry: 'ADRs',
  technical_debt_registry: 'Debt',
  platform_health_registry: 'Health',
};

export function buildConstitutionCountCards(snapshot: ConstitutionConsoleSnapshot): ConstitutionCountCard[] {
  return Object.entries(COUNT_LABELS).map(([id, label]) => ({
    id,
    label,
    value: Number(snapshot.overview.registries[id] ?? 0),
  }));
}

export function buildConstitutionListCards(snapshot: ConstitutionConsoleSnapshot): ConstitutionListCard[] {
  return [
    {
      id: 'missions',
      label: 'Active missions',
      empty: 'No missions recorded yet.',
      items: snapshot.missions.items.map((item) => `${item.title} · ${item.status} · ${item.risk}`),
    },
    {
      id: 'decisions',
      label: 'Recent decisions',
      empty: 'No constitution decisions recorded yet.',
      items: snapshot.decisions.items.map((item) => `${item.actor}: ${item.decision} · ${item.tier || 'unclassified'}`),
    },
    {
      id: 'capabilities',
      label: 'Capabilities',
      empty: 'No capabilities registered yet.',
      items: snapshot.capabilities.items.map((item) => `${item.capability_id} · ${item.name} · ${item.status}`),
    },
    {
      id: 'adrs',
      label: 'Architecture decisions',
      empty: 'No ADRs indexed yet.',
      items: snapshot.adrs.items.map((item) => `ADR-${String(item.number).padStart(3, '0')} · ${item.title} · ${item.status}`),
    },
    {
      id: 'debt',
      label: 'Technical debt',
      empty: 'No open debt records.',
      items: snapshot.debt.items.map((item) => `${item.severity.toUpperCase()} · ${item.title} · ${item.area || 'general'}`),
    },
    {
      id: 'health',
      label: 'Platform health',
      empty: 'No health snapshots captured yet.',
      items: snapshot.health.items.map((item) => `${item.scope} · ${item.status} · ${item.source || 'manual'}`),
    },
  ];
}
