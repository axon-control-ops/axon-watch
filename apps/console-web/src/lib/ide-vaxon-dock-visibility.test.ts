import { describe, expect, it } from 'vitest';

import { shouldShowIdeVaxonDock } from './ide-vaxon-dock-visibility';

describe('shouldShowIdeVaxonDock', () => {
  it('keeps the dock visible outside team view', () => {
    expect(
      shouldShowIdeVaxonDock({
        layoutMode: 'ide',
        ideActivityView: 'explorer',
        workspaceId: 'workspace_dashpro',
        kairoSpeechActive: false,
        liveSpokenText: null,
        stickySpokenText: 'Lead reviews are ready',
        stickyNeedsDecision: false,
      }),
    ).toBe(true);
  });

  it('hides the dock on team view when VAXON is idle', () => {
    expect(
      shouldShowIdeVaxonDock({
        layoutMode: 'ide',
        ideActivityView: 'team',
        workspaceId: 'workspace_dashpro',
        kairoSpeechActive: false,
        liveSpokenText: null,
        stickySpokenText: 'Lead reviews are ready in Mission Control.',
        stickyNeedsDecision: false,
      }),
    ).toBe(false);
  });

  it('shows the dock while VAXON is speaking on team view', () => {
    expect(
      shouldShowIdeVaxonDock({
        layoutMode: 'ide',
        ideActivityView: 'team',
        workspaceId: 'workspace_dashpro',
        kairoSpeechActive: true,
        liveSpokenText: 'Running verification now.',
        stickySpokenText: null,
        stickyNeedsDecision: false,
      }),
    ).toBe(true);
  });

  it('shows the dock for decision prompts awaiting a reply', () => {
    expect(
      shouldShowIdeVaxonDock({
        layoutMode: 'ide',
        ideActivityView: 'team',
        workspaceId: 'workspace_dashpro',
        kairoSpeechActive: false,
        liveSpokenText: null,
        stickySpokenText: 'Should I start verification for Marco now?',
        stickyNeedsDecision: true,
      }),
    ).toBe(true);
  });

  it('shows the dock when the operator pins VAXON from the activity bar', () => {
    expect(
      shouldShowIdeVaxonDock({
        layoutMode: 'ide',
        ideActivityView: 'team',
        workspaceId: 'workspace_dashpro',
        kairoSpeechActive: false,
        liveSpokenText: null,
        stickySpokenText: null,
        stickyNeedsDecision: false,
        operatorPinned: true,
      }),
    ).toBe(true);
  });
});
