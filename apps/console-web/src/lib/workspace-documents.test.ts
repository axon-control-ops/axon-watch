import { describe, expect, it } from 'vitest';

import type { InboxItem, RunRecord, RuntimeSummary, WorkspaceRecord } from '../contracts/canonical';
import { buildWorkspaceDocuments } from './workspace-documents';

const workspace: WorkspaceRecord = { workspace_id: 'workspace_alpha' };

const run: RunRecord = {
  run_id: 'run_alpha',
  workspace_id: 'workspace_alpha',
  lane_id: 'control-plane',
  mode: 'agent',
  status: 'running',
  phase: 'executing',
  summary: 'Workspace run',
  detail: 'Bound to editor documents',
  started_at: '2026-07-04T08:00:00Z',
  updated_at: '2026-07-04T08:00:00Z',
  ended_at: null,
  can_stop: true,
  can_resume: false,
  can_approve: false,
  can_review: false,
  current_step: 'Executing',
  history_ref: 'history/run_alpha',
};

const runtimeSummary: RuntimeSummary = {
  generated_at: '2026-07-04T08:00:00Z',
  control_plane: { status: 'ok', version: '0.1.0', uptime_seconds: 10, ready: true },
  watch: {
    status: 'ok',
    connected: true,
    last_summary_at: '2026-07-04T08:00:00Z',
    degraded_reason: null,
  },
  runtime_identity: {
    provider_family: 'bootstrap',
    provider_name: 'Axon-X Bootstrap',
    model_name: 'bootstrap-model',
    mode_default: 'agent',
    tool_calling_supported: false,
    reasoning_supported: false,
  },
  active_runs: [],
  approvals: { pending_count: 0, highest_severity: null, latest_approval_at: null },
  signals: {
    open_count: 1,
    critical_count: 0,
    high_count: 1,
    top_items: [],
    last_updated_at: '2026-07-04T08:00:00Z',
  },
  capabilities: {
    editor: true,
    terminal: true,
    browser_preview: true,
    watch_connected: true,
    approvals_enabled: true,
    notifications_enabled: false,
  },
  degraded: { active: false, reasons: [] },
};

const signal: InboxItem = {
  signal_id: 'signal_runtime_summary_degraded',
  workspace_id: 'workspace_alpha',
  title: 'Watch summary degraded',
  summary: 'Watch summary is degraded.',
  severity: 'high',
  status: 'open',
  source: 'watch',
  created_at: '2026-07-04T08:00:00Z',
  updated_at: '2026-07-04T08:00:00Z',
  action_type: 'open_dashboard',
};

describe('workspace documents', () => {
  it('builds workspace-bound document set from canonical DTOs', () => {
    const documents = buildWorkspaceDocuments({
      workspace,
      runs: [run],
      runtimeSummary,
      primaryInboxItem: signal,
    });

    expect(documents.map((document) => document.id)).toEqual([
      'workspace-overview',
      'workspace-run-record',
      'workspace-runtime-summary',
      'workspace-top-signal',
    ]);
    expect(documents[0]?.value).toContain('Workspace workspace_alpha');
    expect(documents[1]?.value).toContain('"run_id": "run_alpha"');
    expect(documents[3]?.value).toContain('"signal_id": "signal_runtime_summary_degraded"');
  });
});
