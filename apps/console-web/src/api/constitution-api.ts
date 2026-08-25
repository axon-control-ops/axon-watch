import { fetchJson } from './client';

export interface ConstitutionRegistryCounts {
  evidence_registry: number;
  mission_registry: number;
  decision_registry: number;
  capability_registry: number;
  adr_registry: number;
  technical_debt_registry: number;
  platform_health_registry: number;
  [key: string]: number;
}

export interface ConstitutionOverviewSnapshot {
  status: string;
  registries: ConstitutionRegistryCounts;
  source_of_truth: string;
}

export interface ConstitutionListSnapshot<T> {
  items: T[];
  count: number;
}

export interface ConstitutionMissionRecord {
  mission_id: string;
  workspace_id: string;
  title: string;
  description?: string;
  status: string;
  risk: string;
  lead_plan_id?: string | null;
  success_criteria?: string[];
  updated_at?: string;
}

export interface ConstitutionDecisionRecord {
  decision_id: string;
  actor: string;
  capability_id?: string;
  decision: string;
  tier: string;
  risk: string;
  explanation?: string;
  evidence_ids?: string[];
  created_at?: string;
}

export interface ConstitutionCapabilityRecord {
  capability_id: string;
  name: string;
  status: string;
  owner_role?: string;
  version?: string;
}

export interface ConstitutionAdrRecord {
  adr_id: string;
  number: number;
  title: string;
  status: string;
  doc_path?: string;
}

export interface ConstitutionDebtRecord {
  debt_id: string;
  title: string;
  severity: string;
  area: string;
  status: string;
}

export interface ConstitutionHealthRecord {
  snapshot_id: string;
  scope: string;
  status: string;
  source?: string;
  created_at?: string;
}

export interface ConstitutionEvidenceRecord {
  evidence_id: string;
  source_table: string;
  source_id: string;
  kind: string;
  summary?: string;
  workspace_id?: string;
  run_id?: string | null;
  task_id?: string | null;
  mission_id?: string | null;
  decision_id?: string | null;
}

export interface ConstitutionConsoleSnapshot {
  overview: ConstitutionOverviewSnapshot;
  missions: ConstitutionListSnapshot<ConstitutionMissionRecord>;
  decisions: ConstitutionListSnapshot<ConstitutionDecisionRecord>;
  capabilities: ConstitutionListSnapshot<ConstitutionCapabilityRecord>;
  adrs: ConstitutionListSnapshot<ConstitutionAdrRecord>;
  debt: ConstitutionListSnapshot<ConstitutionDebtRecord>;
  health: ConstitutionListSnapshot<ConstitutionHealthRecord>;
  evidence: ConstitutionListSnapshot<ConstitutionEvidenceRecord>;
}

export async function fetchConstitutionOverview(): Promise<ConstitutionOverviewSnapshot> {
  return fetchJson<ConstitutionOverviewSnapshot>(
    '/api/operator/constitution',
    {},
    'constitution overview request failed',
  );
}

export async function fetchConstitutionConsoleSnapshot(): Promise<ConstitutionConsoleSnapshot> {
  const [overview, missions, decisions, capabilities, adrs, debt, health, evidence] = await Promise.all([
    fetchConstitutionOverview(),
    fetchJson<ConstitutionListSnapshot<ConstitutionMissionRecord>>(
      '/api/operator/constitution/missions?limit=10',
      {},
      'constitution missions request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionDecisionRecord>>(
      '/api/operator/constitution/decisions?limit=10',
      {},
      'constitution decisions request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionCapabilityRecord>>(
      '/api/operator/constitution/capabilities?limit=20',
      {},
      'constitution capabilities request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionAdrRecord>>(
      '/api/operator/constitution/adrs?limit=10',
      {},
      'constitution ADRs request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionDebtRecord>>(
      '/api/operator/constitution/debt?limit=10',
      {},
      'constitution debt request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionHealthRecord>>(
      '/api/operator/constitution/health?limit=10',
      {},
      'constitution health request failed',
    ),
    fetchJson<ConstitutionListSnapshot<ConstitutionEvidenceRecord>>(
      '/api/operator/constitution/evidence?limit=10',
      {},
      'constitution evidence request failed',
    ),
  ]);

  return { overview, missions, decisions, capabilities, adrs, debt, health, evidence };
}
