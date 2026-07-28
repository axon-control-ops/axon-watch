import { describe, expect, it } from 'vitest';

import {
  buildVaxonReportDirectives,
  isAutoExecutableCommitment,
  matchActionForNextMove,
  stageSpokenLine,
  toVaxonDirectiveLine,
} from './report-theater-directives';

describe('report-theater-directives', () => {
  it('rewrites passive next-move copy into VAXON first person', () => {
    expect(
      toVaxonDirectiveLine(
        'Critical signal in DashPro needs review; switch there before continuing',
      ),
    ).toMatch(/^I'll switch us there/i);
  });

  it('rewrites inspect advise into Attention open', () => {
    expect(toVaxonDirectiveLine('Inspect DashPro Sentry critical')).toMatch(
      /^I'll open Attention for DashPro Sentry critical/i,
    );
  });

  it('matches primary action to the named signal instead of actions[0]', () => {
    const sentry = {
      action_id: 'a-sentry',
      kind: 'review_signal' as const,
      title: 'DashPro Sentry critical',
      detail: 'outside the app',
      workspace_id: 'workspace_dashpro',
      run_id: null,
      signal_id: 'sig-sentry',
    };
    const runtime = {
      action_id: 'a-runtime',
      kind: 'inspect_runtime' as const,
      title: 'Runtime',
      detail: 'CLI not ready',
      workspace_id: null,
      run_id: null,
      signal_id: null,
    };
    expect(
      matchActionForNextMove("I'll switch us there and review that signal next", [
        runtime,
        sentry,
      ])?.action_id,
    ).toBe('a-sentry');
  });

  it('matches a promised workspace switch before the first review action', () => {
    const actions = [
      {
        action_id: 'dash',
        kind: 'review_signal' as const,
        title: 'DashPro warning',
        detail: 'DashPro',
        workspace_id: 'workspace_dashpro',
        run_id: null,
        signal_id: 'sig-dash',
      },
      {
        action_id: 'axon',
        kind: 'review_signal' as const,
        title: 'Axon-X warning',
        detail: 'Axon Watch',
        workspace_id: 'workspace_axon_watch',
        run_id: null,
        signal_id: 'sig-axon',
      },
    ];
    expect(
      matchActionForNextMove("I'll switch to axon-watch and review that signal next", actions)
        ?.action_id,
    ).toBe('axon');
  });

  it('synthesizes signal actions when next_safe_actions are empty', () => {
    const directives = buildVaxonReportDirectives({
      nextMove: "I'll switch us there and review that signal next",
      actions: [],
      topSignals: [
        {
          signal_id: 'sig-dash',
          title: 'DashPro Sentry critical',
          summary: 'outside the app',
          workspace_id: 'workspace_dashpro',
        },
      ],
    });
    expect(directives[0]?.briefingAction?.kind).toBe('review_signal');
    expect(directives[0]?.autoExecute).toBe(true);
    expect(isAutoExecutableCommitment(directives[0]!.label, directives[0]!.briefingAction)).toBe(
      true,
    );
  });

  it('binds the action to the workspace VAXON names even when signal metadata is stale', () => {
    const directives = buildVaxonReportDirectives({
      nextMove: "I'll switch to DashPro and review that signal next",
      actions: [
        {
          action_id: 'cloudflare',
          kind: 'review_signal',
          title: 'Cloudflare tunnel unavailable',
          detail: 'Inspect tunnel',
          workspace_id: 'workspace_axon_watch',
          run_id: null,
          signal_id: 'sig-cloudflare',
        },
      ],
      workspaces: [
        { workspace_id: 'workspace_axon_watch', display_name: 'axon-watch' },
        { workspace_id: 'workspace_dashpro', display_name: 'DashPro' },
      ],
    });

    expect(directives[0]?.label).toBe(
      "I'll switch to DashPro and start that investigation next",
    );
    expect(directives[0]?.briefingAction?.workspace_id).toBe('workspace_dashpro');
  });

  it('compresses completed-work lists for fluent speech', () => {
    expect(
      stageSpokenLine('Work in flight', [
        'Reed (Backend) just completed',
        'Jules (Frontend) just completed',
        'Quinn (Integrations) just completed',
      ]),
    ).toBe('Work in flight. Reed (Backend), Jules (Frontend), Quinn (Integrations) just wrapped.');
  });

  it('keeps filler stages short', () => {
    expect(stageSpokenLine('Lead rollups', ['None verified yet.'])).toBe(
      'Lead rollups — Lead standing by.',
    );
  });

  it('speaks Lead rollups in the Lead voice', () => {
    expect(
      stageSpokenLine('Lead rollups', [
        'Mira: Rowan failed. Issue is the last shift outcome. Plan: diagnose the failure, then requeue the smallest fix.',
      ]),
    ).toBe(
      'Mira here. Rowan failed. Issue is the last shift outcome. Plan: diagnose the failure, then requeue the smallest fix',
    );
  });

  it('synthesizes a workspace switch when next-move names a workspace but actions are empty', () => {
    const directives = buildVaxonReportDirectives({
      nextMove: "I'll switch to axon-watch and start that investigation next",
      actions: [],
      topSignals: [],
      workspaces: [
        { workspace_id: 'workspace_axon_watch', display_name: 'axon-watch' },
        { workspace_id: 'workspace_edudashpro_school', display_name: 'EDP Excellence' },
      ],
    });
    expect(directives[0]?.briefingAction?.kind).toBe('review_signal');
    expect(directives[0]?.briefingAction?.workspace_id).toBe('workspace_axon_watch');
    expect(directives[0]?.autoExecute).toBe(true);
    expect(directives[0]?.detail).toMatch(/executes this next/i);
  });
});
