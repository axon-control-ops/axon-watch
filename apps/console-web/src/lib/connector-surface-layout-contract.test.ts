import { describe, expect, it } from 'vitest';

import { readCss, ruleBlock } from './css-layout-contract-helpers';

describe('watch connector surface layout contract', () => {
  it('loads watch connector rail styles from the mockup-shell aggregator', () => {
    const aggregator = readCss('mockup-shell.css');
    expect(aggregator).toMatch(
      /@import\s+['"]\.\/shell\/mockup-shell-connectors-rail\.css['"]/,
    );

    const shell11 = readCss('shell/mockup-shell-11.css');
    const shell17 = readCss('shell/mockup-shell-17.css');
    const shell18 = readCss('shell/mockup-shell-18.css');
    expect(shell11).not.toMatch(/\.connectors-rail-panel/);
    expect(shell17).not.toMatch(/\.connectors-rail-panel/);
    expect(shell18).not.toMatch(/\.connectors-rail-panel/);

    const connectorsRail = readCss('shell/mockup-shell-connectors-rail.css');
    const panel = ruleBlock(connectorsRail, '.connectors-rail-panel');
    expect(panel).toMatch(/display:\s*flex/);
    expect(panel).toMatch(/flex-shrink:\s*1/);
    expect(panel).toMatch(/min-height:\s*0/);

    const offlineStatus = ruleBlock(
      connectorsRail,
      '.connectors-rail-panel__status--offline',
    );
    expect(offlineStatus).toMatch(/color:\s*rgba\(251,\s*191,\s*36,\s*0\.88\)/);

    const watchOfflineSummary = ruleBlock(
      connectorsRail,
      '.connectors-rail-panel--watch-offline .connectors-rail-panel__summary',
    );
    expect(watchOfflineSummary).toMatch(/color:\s*rgba\(251,\s*191,\s*36,\s*0\.92\)/);

    const watchOfflineList = ruleBlock(
      connectorsRail,
      '.connectors-rail-panel--watch-offline .connectors-rail-panel__list',
    );
    expect(watchOfflineList).toMatch(/opacity:\s*0\.78/);

    const watchOfflineItem = ruleBlock(
      connectorsRail,
      '.connectors-rail-panel--watch-offline .connectors-rail-panel__item',
    );
    expect(watchOfflineItem).toMatch(/border-color:\s*rgba\(255,\s*255,\s*255,\s*0\.04\)/);

    const probeDetail = ruleBlock(connectorsRail, '.connectors-rail-panel__item-detail');
    expect(probeDetail).toMatch(/font-size:\s*0\.64rem/);
    expect(probeDetail).toMatch(/color:\s*var\(--text-muted\)/);
  });

  it('styles the watch-offline status-bar chip as a warning affordance', () => {
    const shell28 = readCss('shell/mockup-shell-28.css');
    const chip = ruleBlock(shell28, '.status-bar-mockup__chip--watch-offline');
    expect(chip).toMatch(/cursor:\s*pointer/);
    expect(chip).toMatch(/border-style:\s*dashed/);
    expect(chip).toMatch(/border-color:\s*rgba\(255,\s*176,\s*96/);

    const icon = ruleBlock(shell28, '.status-bar-mockup__icon--watch-offline');
    expect(icon).toMatch(/border:\s*1px dashed rgba\(255,\s*176,\s*96/);
  });

  it('styles the IDE editor status-bar required-down chip with a solid amber affordance', () => {
    const panels = readCss('shell/editor-statusbar-panels.css');
    const chip = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--connector-required-alert',
    );
    expect(chip).toMatch(/border-color:\s*rgba\(255,\s*176,\s*96,\s*0\.38\)/);
    expect(chip).toMatch(/background:\s*rgba\(32,\s*18,\s*8,\s*0\.92\)/);
    expect(chip).not.toMatch(/border-style:\s*dashed/);

    const focus = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--connector-required-alert:focus-visible',
    );
    expect(focus).toMatch(/outline:\s*2px solid rgba\(255,\s*176,\s*96,\s*0\.72\)/);
    expect(focus).toMatch(/outline-offset:\s*2px/);

    const icon = ruleBlock(panels, '.editor-statusbar__panel-icon--connector-required-alert');
    expect(icon).toMatch(/border:\s*1px solid rgba\(255,\s*176,\s*96,\s*0\.72\)/);
    expect(icon).toMatch(/background:\s*rgba\(255,\s*176,\s*96,\s*0\.28\)/);
    expect(icon).toMatch(/border-radius:\s*50%/);
  });

  it('styles the IDE editor status-bar watch-offline chip with a dashed affordance', () => {
    const panels = readCss('shell/editor-statusbar-panels.css');
    const chip = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--connector-watch-offline',
    );
    expect(chip).toMatch(/border-style:\s*dashed/);
    expect(chip).toMatch(/border-color:\s*rgba\(255,\s*176,\s*96/);
    expect(chip).toMatch(/color:\s*rgba\(255,\s*196,\s*128/);

    const focus = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--connector-watch-offline:focus-visible',
    );
    expect(focus).toMatch(/outline:\s*2px solid rgba\(255,\s*176,\s*96,\s*0\.72\)/);
    expect(focus).toMatch(/outline-offset:\s*2px/);

    const icon = ruleBlock(panels, '.editor-statusbar__panel-icon--watch-offline');
    expect(icon).toMatch(/border:\s*1px dashed rgba\(255,\s*176,\s*96,\s*0\.72\)/);
    expect(icon).toMatch(/border-radius:\s*50%/);

    const requiredAlert = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--connector-required-alert',
    );
    expect(requiredAlert).not.toMatch(/border-style:\s*dashed/);
  });

  it('loads connector attention pulse styles from the ide-layout aggregator', () => {
    const aggregator = readCss('ide-layout.css');
    expect(aggregator).toMatch(
      /@import\s+['"]\.\/ide\/ide-layout-01-connector-attention\.css['"]/,
    );
    expect(aggregator).toMatch(
      /@import\s+['"]\.\/ide\/ide-layout-01-explorer-stub\.css['"]/,
    );

    const layout01 = readCss('ide/ide-layout-01.css');
    expect(layout01).not.toMatch(/ide-activity-bar-pulse-warning/);
    expect(layout01).not.toMatch(/ide-explorer-stub-stream/);

    const connectorAttention = readCss('ide/ide-layout-01-connector-attention.css');
    const warningPulse = ruleBlock(connectorAttention, '.ide-activity-bar__pulse--warning');
    expect(warningPulse).toMatch(/animation:\s*ide-activity-bar-pulse-warning/);

    const teamAttention = ruleBlock(connectorAttention, '.ide-activity-bar__button--team-attention');
    expect(teamAttention).toMatch(/box-shadow:\s*inset 0 -2px 0 rgba\(190,\s*80,\s*60,\s*0\.42\)/);

    const teamAttentionInterrupted = ruleBlock(
      connectorAttention,
      '.ide-activity-bar__button--team-attention-interrupted',
    );
    expect(teamAttentionInterrupted).toMatch(
      /box-shadow:\s*inset 0 -2px 0 rgba\(255,\s*180,\s*90,\s*0\.42\)/,
    );

    const teamAttentionMixed = ruleBlock(
      connectorAttention,
      '.ide-activity-bar__button--team-attention-mixed',
    );
    expect(teamAttentionMixed).toMatch(
      /box-shadow:\s*inset 0 -2px 0 rgba\(255,\s*150,\s*110,\s*0\.42\)/,
    );

    const teamBadge = ruleBlock(connectorAttention, '.ide-activity-bar__badge--failure');
    expect(teamBadge).toMatch(/border-color:\s*rgba\(255,\s*130,\s*105,\s*0\.52\)/);

    const teamBadgeInterrupted = ruleBlock(connectorAttention, '.ide-activity-bar__badge--interrupted');
    expect(teamBadgeInterrupted).toMatch(/border-color:\s*rgba\(255,\s*180,\s*90,\s*0\.48\)/);

    const teamBadgeMixed = ruleBlock(connectorAttention, '.ide-activity-bar__badge--mixed');
    expect(teamBadgeMixed).toMatch(/border-color:\s*rgba\(255,\s*150,\s*110,\s*0\.46\)/);

    const gitAttention = ruleBlock(connectorAttention, '.ide-activity-bar__button--git-attention');
    expect(gitAttention).toMatch(/box-shadow:\s*inset 0 -2px 0 rgba\(0,\s*242,\s*255,\s*0\.32\)/);

    const gitBadge = ruleBlock(connectorAttention, '.ide-activity-bar__badge--dirty');
    expect(gitBadge).toMatch(/border-color:\s*rgba\(0,\s*242,\s*255,\s*0\.42\)/);

    const teamPanelAttention = ruleBlock(connectorAttention, '.ide-team-panel--attention');
    expect(teamPanelAttention).toMatch(/box-shadow:\s*inset 0 0 0 1px rgba\(255,\s*110,\s*90,\s*0\.28\)/);

    const teamPanelAttentionInterrupted = ruleBlock(
      connectorAttention,
      '.ide-team-panel--attention-interrupted',
    );
    expect(teamPanelAttentionInterrupted).toMatch(
      /box-shadow:\s*inset 0 0 0 1px rgba\(255,\s*180,\s*90,\s*0\.28\)/,
    );

    const teamPanelAttentionMixed = ruleBlock(
      connectorAttention,
      '.ide-team-panel--attention-mixed',
    );
    expect(teamPanelAttentionMixed).toMatch(
      /box-shadow:\s*inset 0 0 0 1px rgba\(255,\s*150,\s*110,\s*0\.28\)/,
    );

    const gitPanelAttention = ruleBlock(connectorAttention, '.ide-explorer-panel--git-attention');
    expect(gitPanelAttention).toMatch(/box-shadow:\s*inset 0 0 0 1px rgba\(0,\s*242,\s*255,\s*0\.22\)/);

    const searchAttention = ruleBlock(connectorAttention, '.ide-activity-bar__button--search-attention');
    expect(searchAttention).toMatch(/box-shadow:\s*inset 0 -2px 0 rgba\(255,\s*180,\s*120,\s*0\.38\)/);

    const searchPanelAttention = ruleBlock(connectorAttention, '.ide-explorer-panel--search-attention');
    expect(searchPanelAttention).toMatch(/box-shadow:\s*inset 0 0 0 1px rgba\(255,\s*180,\s*120,\s*0\.24\)/);

    const explorerStub = readCss('ide/ide-layout-01-explorer-stub.css');
    const runNoticeAction = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-attention .ide-explorer-panel__stub-action:focus-visible',
    );
    expect(runNoticeAction).toMatch(/border-color:\s*rgba\(255,\s*200,\s*110,\s*0\.52\)/);

    const stubActionFocus = ruleBlock(
      explorerStub,
      '.ide-explorer-panel__stub-action:focus-visible',
    );
    expect(stubActionFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(stubActionFocus).toMatch(/outline-offset:\s*2px/);

    const streamingAction = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-streaming .ide-explorer-panel__stub-action',
    );
    expect(streamingAction).toMatch(/border-color:\s*rgba\(120,\s*200,\s*255,\s*0\.34\)/);

    const stubActions = ruleBlock(explorerStub, '.ide-explorer-panel__stub-actions');
    expect(stubActions).toMatch(/display:\s*flex/);
    expect(stubActions).toMatch(/flex-wrap:\s*wrap/);

    const secondaryRetry = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-failure .ide-explorer-panel__stub-action--secondary',
    );
    expect(secondaryRetry).toMatch(/box-shadow:\s*0 0 10px rgba\(160,\s*60,\s*40,\s*0\.18\)/);

    const failurePrimaryOutline = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-failure .ide-explorer-panel__stub-action:not(.ide-explorer-panel__stub-action--secondary)',
    );
    expect(failurePrimaryOutline).toMatch(/border-color:\s*rgba\(140,\s*190,\s*230,\s*0\.32\)/);

    const interruptedSecondary = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-interrupted .ide-explorer-panel__stub-action--secondary',
    );
    expect(interruptedSecondary).toMatch(/border-color:\s*rgba\(255,\s*180,\s*90,\s*0\.48\)/);

    const neutralRunNotice = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-neutral:has(.ide-explorer-panel__run-notice)',
    );
    expect(neutralRunNotice).toMatch(/box-shadow:\s*inset 0 0 0 1px rgba\(120,\s*200,\s*255,\s*0\.18\)/);

    const neutralRunNoticeAction = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-neutral:has(.ide-explorer-panel__run-notice) .ide-explorer-panel__stub-action',
    );
    expect(neutralRunNoticeAction).toMatch(/border-color:\s*rgba\(120,\s*200,\s*255,\s*0\.28\)/);

    const attentionRunNotice = ruleBlock(
      explorerStub,
      '.ide-explorer-panel--stub-attention .ide-explorer-panel__run-notice',
    );
    expect(attentionRunNotice).toMatch(/border-bottom-color:\s*rgba\(255,\s*180,\s*120,\s*0\.22\)/);
  });
});
