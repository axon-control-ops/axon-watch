import { describe, expect, it } from 'vitest';

import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import exampleRuntimeSummary from '../../../../packages/shared-types/fixtures/runtime-summary.example.json';
import {
  buildBriefingHeroSubtitle,
  buildBriefingSummaryLine,
  buildMockupTopbarBreadcrumb,
  buildStatusBarZones,
  buildTopbarBreadcrumb,
  buildTopbarMetaPills,
  buildTopbarRuntimeVersionChips,
  buildWorkspaceStatusCardRows,
  kairoPresenceModuleLabel,
  kairoPresenceModuleParts,
  mergeMockupWorkspaceCatalog,
  resolveBootstrapWorkspaceId,
  resolveOperatorWorkspaceId,
  runPhaseProgress,
  runPhaseTag,
  workspaceStatusLine,
} from './mockup-shell-view';
import { workspaceIconKind } from './mockup-workspace-icons';

const runtimeSummary = exampleRuntimeSummary as RuntimeSummary;
const briefing = exampleBriefing as unknown as OperatorBriefing;

describe('mockup shell view helpers', () => {
  it('omits the legacy mockup topbar breadcrumb', () => {
    expect(buildMockupTopbarBreadcrumb()).toBe('');
  });

  it('omits the legacy runtime version chips', () => {
    expect(buildTopbarRuntimeVersionChips(runtimeSummary)).toEqual([]);
  });

  it('builds topbar meta pills from runtime summary', () => {
    expect(buildTopbarMetaPills(runtimeSummary)).toEqual([
      { id: 'runtime', label: 'RUNTIME READY', tone: 'success' },
      { id: 'control-plane', label: 'CP v0.1.0', tone: 'brand' },
      { id: 'model', label: 'GPT-5.4', tone: 'brand' },
      { id: 'watch', label: 'WATCH ONLINE', tone: 'success' },
    ]);
  });

  it('builds breadcrumb from workspace and runtime identity', () => {
    expect(buildTopbarBreadcrumb(runtimeSummary, { workspace_id: 'workspace_smoke' } as never)).toBe(
      'workspace_smoke / OpenAI / gpt-5.4',
    );
  });

  it('maps executing phase to EXECUTE tag', () => {
    expect(runPhaseProgress('executing')).toBe(68);
    expect(runPhaseTag('executing')).toBe('EXECUTE');
    expect(runPhaseTag('review_ready')).toBe('REVIEW READY');
  });

  it('maps workspace ids to icon kinds for sidebar glyphs', () => {
    expect(workspaceIconKind('workspace_axon_watch')).toBe('cube');
    expect(workspaceIconKind('workspace_axon_local')).toBe('tower');
    expect(workspaceIconKind('workspace_dashpro')).toBe('building');
    expect(workspaceIconKind('workspace_smoke')).toBe('cube');
    expect(workspaceIconKind('workspace_recsys')).toBe('cube');
    expect(workspaceIconKind('workspace_finance')).toBe('building');
    expect(workspaceIconKind('workspace_nlp')).toBe('chat');
  });

  it('builds briefing summary line for mockup card', () => {
    expect(
      buildBriefingSummaryLine(briefing, runtimeSummary, 'workspace_alpha'),
    ).toContain('approval');
  });

  it('uses fleet active signal count when workspace-scoped briefing is empty', () => {
    const emptySignalsBriefing = {
      ...briefing,
      top_signals: [],
      pending_approvals: { ...briefing.pending_approvals, count: 0, items: [] },
    } as OperatorBriefing;

    expect(
      buildBriefingSummaryLine(emptySignalsBriefing, runtimeSummary, 'workspace_axon_watch', 1),
    ).toContain('1 signal require review');
  });

  it('builds briefing hero subtitle without KAIRO prefix', () => {
    expect(buildBriefingHeroSubtitle(briefing, 'loaded')).toBe(briefing.notice);
    expect(buildBriefingHeroSubtitle(briefing, 'loading')).toBe(briefing.notice);
    expect(buildBriefingHeroSubtitle(null, 'loaded')).toBe(
      "I'm listening. Tell me what to focus on.",
    );
    expect(buildBriefingHeroSubtitle(null, 'loading')).toBe(
      "Hang on — I'm still getting your status ready.",
    );
  });

  it('builds three-zone status bar layout from runtime summary', () => {
    const zones = buildStatusBarZones({
      runtimeSummary,
      runtimeSummaryLoadState: 'loaded',
      primaryActiveRun: { phase: 'executing' } as RunRecord,
      workspaceId: 'workspace_smoke',
    });

    expect(zones.left[0]?.label).toBe('WATCH CONNECTED');
    expect(zones.left[1]?.label).toBe('WATCH OK');
    expect(zones.left[2]?.label).toBe('v0.1.0');
    expect(zones.center[0]?.label).toBe('RUN PHASE: EXECUTE');
    expect(zones.right[0]?.label).toBe('WORKSPACE: workspace_smoke');
  });

  it('builds IDE quiet status bar without watch or ops telemetry', () => {
    const zones = buildStatusBarZones({
      runtimeSummary,
      runtimeSummaryLoadState: 'loaded',
      primaryActiveRun: { phase: 'executing' } as RunRecord,
      workspaceId: 'workspace_smoke',
      layoutMode: 'ide',
      idePresenceProfile: 'quiet',
    });

    expect(zones.left.some((item) => item.id === 'watch')).toBe(false);
    expect(zones.left[0]?.id).toBe('workspace');
    expect(zones.center).toEqual([]);
  });

  it('builds workspace status card rows from runtime summary', () => {
    const rows = buildWorkspaceStatusCardRows({
      runtimeSummary,
      runtimeSummaryLoadState: 'loaded',
    });

    expect(rows).toEqual([
      { label: 'Environment', value: 'dev-west-1' },
      { label: 'Last Activity', value: expect.any(String) },
      { label: 'Storage', value: '42.7 GB' },
      { label: 'Signals', value: '1' },
    ]);
  });

  it('uppercases KAIRO presence module labels', () => {
    expect(kairoPresenceModuleLabel('observing')).toBe('VAXON WATCHING');
    expect(kairoPresenceModuleLabel('thinking')).toBe('VAXON CHECKING');
    expect(kairoPresenceModuleLabel('alerting')).toBe('VAXON ATTENTION');
  });

  it('splits KAIRO presence into title and subtitle', () => {
    expect(kairoPresenceModuleParts('alerting')).toEqual({
      title: 'VAXON',
      subtitle: 'ATTENTION',
    });
  });

  it('merges mockup workspace catalog without catalog-only extras', () => {
    const merged = mergeMockupWorkspaceCatalog([{ workspace_id: 'workspace_alpha' }]);
    expect(merged[0]?.workspace_id).toBe('workspace_smoke');
    expect(merged.some((item) => item.workspace_id === 'workspace_alpha')).toBe(false);
    expect(merged).toHaveLength(7);
  });

  it('resolves bootstrap workspace from active run when visible', () => {
    const workspaces = mergeMockupWorkspaceCatalog([]);
    expect(
      resolveBootstrapWorkspaceId(workspaces, {
        run_id: 'run_1',
        workspace_id: 'workspace_finance',
      } as RunRecord),
    ).toBe('workspace_finance');
  });

  it('falls back to workspace_smoke when no active run is visible', () => {
    const workspaces = mergeMockupWorkspaceCatalog([]);
    expect(resolveBootstrapWorkspaceId(workspaces, null)).toBe('workspace_smoke');
  });

  it('keeps operator-pinned workspace over active-run bootstrap default', () => {
    const workspaces = mergeMockupWorkspaceCatalog([]);
    expect(
      resolveOperatorWorkspaceId({
        pinnedWorkspaceId: 'workspace_recsys',
        workspaces,
        activeRun: {
          run_id: 'run_1',
          workspace_id: 'workspace_smoke',
        } as RunRecord,
      }),
    ).toBe('workspace_recsys');
  });

  it('still follows visible active run when operator has not pinned a workspace', () => {
    const workspaces = mergeMockupWorkspaceCatalog([]);
    expect(
      resolveOperatorWorkspaceId({
        workspaces,
        activeRun: {
          run_id: 'run_1',
          workspace_id: 'workspace_finance',
        } as RunRecord,
      }),
    ).toBe('workspace_finance');
  });

  it('prefers visible run workspace over default on bootstrap reload', () => {
    const workspaces = mergeMockupWorkspaceCatalog([]);
    expect(
      resolveBootstrapWorkspaceId(workspaces, {
        run_id: 'run_1',
        workspace_id: 'workspace_alpha',
      } as RunRecord),
    ).toBe('workspace_smoke');
  });

  it('builds workspace status lines with idle and active run counts', () => {
    expect(workspaceStatusLine('workspace_smoke', true, { workspace_smoke: 13 })).toBe(
      'Active • 13 active runs',
    );
    expect(workspaceStatusLine('workspace_finance', false, { workspace_finance: 2 })).toBe(
      '2 active runs',
    );
    expect(workspaceStatusLine('workspace_finance', false)).toBe('Idle');
    expect(workspaceStatusLine('workspace_smoke', true)).toBe('Selected • idle');
  });
});
