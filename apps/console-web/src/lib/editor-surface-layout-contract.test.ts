import { describe, expect, it } from 'vitest';

import { readCss, ruleBlock } from './css-layout-contract-helpers';

describe('IDE editor surface layout contract', () => {
  it('keeps Monaco editor host relative (EditContext-safe; do not absolute-collapse)', () => {
    const shell07 = readCss('shell/mockup-shell-07.css');
    expect(shell07).toMatch(/@import\s+['"]\.\/mockup-shell-07-monaco\.css['"]/);

    const body = ruleBlock(shell07, '.center-workbench__editor .surface-host__body--editor');
    expect(body).toMatch(/position:\s*relative/);
    expect(body).toMatch(/isolation:\s*isolate/);

    const monaco = readCss('shell/mockup-shell-07-monaco.css');
    const frame = ruleBlock(monaco, '.center-workbench__editor .surface-host__frame--editor');
    expect(frame).toMatch(/position:\s*relative/);
    expect(frame).not.toMatch(/position:\s*absolute/);
  });

  it('styles editor chrome tab, tool, and breadcrumb focus rings for keyboard navigation', () => {
    const shell06 = readCss('shell/mockup-shell-06.css');
    const breadcrumbFocus = ruleBlock(
      shell06,
      '.editor-breadcrumb__segment:not(:disabled):focus-visible',
    );
    expect(breadcrumbFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(breadcrumbFocus).toMatch(/outline-offset:\s*1px/);

    const shell07 = readCss('shell/mockup-shell-07.css');
    const tabSelectFocus = ruleBlock(shell07, '.editor-tabbar__tab-select:focus-visible');
    expect(tabSelectFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(tabSelectFocus).toMatch(/outline-offset:\s*-2px/);

    const tabCloseFocus = ruleBlock(shell07, '.editor-tabbar__close:focus-visible');
    expect(tabCloseFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(tabCloseFocus).toMatch(/outline-offset:\s*1px/);

    const shell08 = readCss('shell/mockup-shell-08.css');
    const toolFocus = ruleBlock(
      shell08,
      '.editor-tabbar__tool-button:focus-visible:not(:disabled)',
    );
    expect(toolFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(toolFocus).toMatch(/outline-offset:\s*2px/);
  });

  it('loads plan/ask styles from the mockup-shell aggregator (not a trailing import)', () => {
    const aggregator = readCss('mockup-shell.css');
    expect(aggregator).toMatch(/@import\s+['"]\.\/shell\/mockup-shell-plan-ask\.css['"]/);

    const shell22 = readCss('shell/mockup-shell-22.css');
    expect(shell22).not.toMatch(/@import\s+['"].*mockup-shell-plan-ask/);

    const planAsk = readCss('shell/mockup-shell-plan-ask.css');
    const option = ruleBlock(planAsk, '.agent-block__question-option');
    expect(option).toMatch(/display:\s*grid/);
    expect(option).toMatch(/grid-template-columns:\s*auto\s+auto\s+minmax\(0,\s*1fr\)/);
    expect(option).toMatch(/column-gap:\s*0\.5rem/);
  });

  it('styles the IDE editor status-bar unsaved-file chip with cyan attention', () => {
    const panels = readCss('shell/editor-statusbar-panels.css');
    const chip = ruleBlock(panels, '.editor-statusbar__panel-toggle--git-unsaved');
    expect(chip).toMatch(/border-color:\s*rgba\(0,\s*242,\s*255,\s*0\.32\)/);
    expect(chip).toMatch(/box-shadow:\s*inset 0 -1px 0 rgba\(0,\s*242,\s*255,\s*0\.32\)/);

    const focus = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--git-unsaved:focus-visible',
    );
    expect(focus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.55\)/);
    expect(focus).toMatch(/outline-offset:\s*2px/);
  });

  it('styles the IDE editor status-bar unsaved save-state control with cyan attention', () => {
    const shell07 = readCss('shell/mockup-shell-07.css');
    expect(shell07).toMatch(/@import\s+['"]\.\/editor-statusbar-meta\.css['"]/);
    expect(shell07).not.toMatch(/\.editor-statusbar__state--unsaved\s*\{/);

    const meta = readCss('shell/editor-statusbar-meta.css');
    const unsaved = ruleBlock(meta, '.editor-statusbar__state--unsaved');
    expect(unsaved).toMatch(/cursor:\s*pointer/);
    expect(unsaved).toMatch(/border:\s*1px solid rgba\(0,\s*242,\s*255,\s*0\.28\)/);
    expect(unsaved).toMatch(/background:\s*rgba\(0,\s*242,\s*255,\s*0\.08\)/);

    const focus = ruleBlock(meta, '.editor-statusbar__state--unsaved:focus-visible');
    expect(focus).toMatch(/outline:\s*1px solid rgba\(0,\s*245,\s*212,\s*0\.55\)/);
    expect(focus).toMatch(/outline-offset:\s*1px/);

    const readOnly = ruleBlock(meta, '.editor-statusbar__state--read-only');
    expect(readOnly).toMatch(/color:\s*rgba\(127,\s*148,\s*168,\s*0\.88\)/);

    const preview = ruleBlock(meta, '.editor-statusbar__state--preview');
    expect(preview).toMatch(/color:\s*rgba\(127,\s*148,\s*168,\s*0\.88\)/);

    const empty = ruleBlock(meta, '.editor-statusbar__state--empty');
    expect(empty).toMatch(/color:\s*rgba\(127,\s*148,\s*168,\s*0\.88\)/);

    const loading = ruleBlock(meta, '.editor-statusbar__state--loading');
    expect(loading).toMatch(/color:\s*rgba\(255,\s*200,\s*130,\s*0\.92\)/);

    const toggleFocus = ruleBlock(meta, '.editor-statusbar__toggle:focus-visible');
    expect(toggleFocus).toMatch(/outline:\s*1px solid rgba\(0,\s*245,\s*212,\s*0\.55\)/);
    expect(toggleFocus).toMatch(/outline-offset:\s*1px/);
  });

  it('styles the IDE editor status-bar search-error chip with amber attention', () => {
    const panels = readCss('shell/editor-statusbar-panels.css');
    const chip = ruleBlock(panels, '.editor-statusbar__panel-toggle--search-error');
    expect(chip).toMatch(/border-color:\s*rgba\(255,\s*180,\s*120,\s*0\.38\)/);
    expect(chip).toMatch(/box-shadow:\s*inset 0 -1px 0 rgba\(255,\s*180,\s*120,\s*0\.38\)/);

    const focus = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--search-error:focus-visible',
    );
    expect(focus).toMatch(/outline:\s*2px solid rgba\(255,\s*200,\s*110,\s*0\.55\)/);
    expect(focus).toMatch(/outline-offset:\s*2px/);
  });

  it('styles the IDE editor status-bar team-attention chips with roster tones', () => {
    const panels = readCss('shell/editor-statusbar-panels.css');
    const failure = ruleBlock(panels, '.editor-statusbar__panel-toggle--team-failure');
    expect(failure).toMatch(/border-color:\s*rgba\(190,\s*80,\s*60,\s*0\.38\)/);
    expect(failure).toMatch(/box-shadow:\s*inset 0 -1px 0 rgba\(190,\s*80,\s*60,\s*0\.42\)/);

    const failureFocus = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--team-failure:focus-visible',
    );
    expect(failureFocus).toMatch(/outline:\s*2px solid rgba\(220,\s*110,\s*90,\s*0\.55\)/);
    expect(failureFocus).toMatch(/outline-offset:\s*2px/);

    const interrupted = ruleBlock(
      panels,
      '.editor-statusbar__panel-toggle--team-interrupted',
    );
    expect(interrupted).toMatch(/border-color:\s*rgba\(255,\s*180,\s*90,\s*0\.38\)/);

    const mixed = ruleBlock(panels, '.editor-statusbar__panel-toggle--team-mixed');
    expect(mixed).toMatch(/border-color:\s*rgba\(255,\s*150,\s*110,\s*0\.38\)/);
  });

  it('loads shared IDE sidebar panel focus styles from the ide-layout aggregator', () => {
    const aggregator = readCss('ide-layout.css');
    expect(aggregator).toMatch(/@import\s+['"]\.\/ide\/ide-panel-shared\.css['"]/);

    const panelShared = readCss('ide/ide-panel-shared.css');
    const searchInputFocus = ruleBlock(panelShared, '.ide-panel-search__input:focus-visible');
    expect(searchInputFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.45\)/);
    expect(searchInputFocus).toMatch(/outline-offset:\s*2px/);

    const searchInputDisabled = ruleBlock(panelShared, '.ide-panel-search__input:disabled');
    expect(searchInputDisabled).toMatch(/cursor:\s*not-allowed/);

    const listButtonFocus = ruleBlock(panelShared, '.ide-panel-list__button:focus-visible');
    expect(listButtonFocus).toMatch(/border-color:\s*rgba\(0,\s*242,\s*255,\s*0\.28\)/);

    const dirtyListButton = ruleBlock(panelShared, '.ide-panel-list__button--dirty');
    expect(dirtyListButton).toMatch(/border-color:\s*rgba\(0,\s*242,\s*255,\s*0\.22\)/);

    const dirtyListDot = ruleBlock(panelShared, '.ide-panel-list__button--dirty::before');
    expect(dirtyListDot).toMatch(/background:\s*rgba\(0,\s*242,\s*255,\s*0\.88\)/);

    const panelActionDisabled = ruleBlock(panelShared, '.ide-panel-action:disabled');
    expect(panelActionDisabled).toMatch(/cursor:\s*not-allowed/);

    const panelRetry = ruleBlock(panelShared, '.ide-panel-retry');
    expect(panelRetry).toMatch(/border:\s*1px solid rgba\(255,\s*180,\s*120,\s*0\.38\)/);
    expect(panelRetry).toMatch(/color:\s*rgba\(255,\s*196,\s*128,\s*0\.96\)/);

    const panelRetryFocus = ruleBlock(panelShared, '.ide-panel-retry:focus-visible:not(:disabled)');
    expect(panelRetryFocus).toMatch(/outline:\s*2px solid rgba\(255,\s*200,\s*110,\s*0\.55\)/);
    expect(panelRetryFocus).toMatch(/outline-offset:\s*2px/);

    const panelRetryDisabled = ruleBlock(panelShared, '.ide-panel-retry:disabled');
    expect(panelRetryDisabled).toMatch(/cursor:\s*not-allowed/);
  });

  it('loads workbench terminal reopen strip styles from the ide-layout aggregator', () => {
    const aggregator = readCss('ide-layout.css');
    expect(aggregator).toMatch(/@import\s+['"]\.\/ide\/ide-layout-08\.css['"]/);

    const layout08 = readCss('ide/ide-layout-08.css');
    expect(layout08).toMatch(/@import\s+['"]\.\/workbench-terminal-reopen\.css['"]/);
    expect(layout08).not.toMatch(/\.workbench-terminal-reopen\s*\{/);

    const reopenCss = readCss('ide/workbench-terminal-reopen.css');
    const reopen = ruleBlock(reopenCss, '.workbench-terminal-reopen');
    expect(reopen).toMatch(/cursor:\s*pointer/);
    expect(reopen).toMatch(/border-top:\s*1px solid/);

    expect(reopenCss).toMatch(
      /\.workbench-terminal-reopen:focus-visible\s*\{[\s\S]*?outline:\s*1px solid rgba\(0,\s*245,\s*212,\s*0\.55\)/,
    );
    expect(reopenCss).toMatch(
      /\.workbench-terminal-reopen:focus-visible\s*\{[\s\S]*?outline-offset:\s*-2px/,
    );

    const reopenAlive = ruleBlock(reopenCss, '.workbench-terminal-reopen--alive');
    expect(reopenAlive).toMatch(/box-shadow:\s*inset 0 2px 0 rgba\(0,\s*220,\s*200,\s*0\.42\)/);

    const reopenExecuting = ruleBlock(reopenCss, '.workbench-terminal-reopen--executing');
    expect(reopenExecuting).toMatch(/animation:\s*workbench-terminal-reopen-stream/);

    const reopenReviewReady = ruleBlock(reopenCss, '.workbench-terminal-reopen--review-ready');
    expect(reopenReviewReady).toMatch(/border-top-color:\s*rgba\(120,\s*200,\s*255,\s*0\.42\)/);
    expect(reopenReviewReady).toMatch(/color:\s*rgba\(190,\s*230,\s*255,\s*0\.98\)/);

    const reducedMotion = ruleBlock(
      reopenCss,
      '@media (prefers-reduced-motion: reduce)',
    );
    expect(reducedMotion).toMatch(/animation:\s*none/);
  });

  it('loads workbench terminal panel surface styles from the shell chain', () => {
    const shell07 = readCss('shell/mockup-shell-07.css');
    expect(shell07).toMatch(/@import\s+['"]\.\/center-workbench-panel-surface\.css['"]/);
    expect(shell07).not.toMatch(/\.center-workbench__panel-surface\s*\{/);

    const panelSurface = readCss('shell/center-workbench-panel-surface.css');
    const surface = ruleBlock(panelSurface, '.center-workbench__panel-surface');
    expect(surface).toMatch(/flex:\s*1/);
    expect(surface).toMatch(/min-height:\s*0/);
    expect(surface).toMatch(/overflow:\s*auto/);

    const problemItem = ruleBlock(panelSurface, '.center-workbench__panel-item--problem');
    expect(problemItem).toMatch(/border-color:\s*rgba\(255,\s*159,\s*0,\s*0\.28\)/);
    expect(problemItem).toMatch(/color:\s*#ffd08a/);

    const markdownToolbar = ruleBlock(panelSurface, '.editor-markdown-toolbar');
    expect(markdownToolbar).toMatch(/display:\s*flex/);
    expect(markdownToolbar).toMatch(/border-bottom:\s*1px solid/);

    const planAsk = readCss('shell/mockup-shell-plan-ask.css');
    const buildPlanFocus = ruleBlock(
      planAsk,
      '.editor-markdown-toolbar__build-plan:focus-visible:not(:disabled)',
    );
    expect(buildPlanFocus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.55\)/);
    expect(buildPlanFocus).toMatch(/outline-offset:\s*2px/);

    const buildPlanDisabled = ruleBlock(planAsk, '.editor-markdown-toolbar__build-plan:disabled');
    expect(buildPlanDisabled).toMatch(/cursor:\s*not-allowed/);
  });

  it('loads quick-guide failure secondary action styles from the shell chain', () => {
    const shell07 = readCss('shell/mockup-shell-07.css');
    expect(shell07).toMatch(/@import\s+['"]\.\/center-workbench-ide-guide\.css['"]/);

    const ideGuide = readCss('shell/center-workbench-ide-guide.css');
    const failureSecondary = ruleBlock(
      ideGuide,
      '.center-workbench__ide-guide--failure .center-workbench__ide-guide-action--secondary',
    );
    expect(failureSecondary).toMatch(/box-shadow:\s*0 0 10px rgba\(160,\s*60,\s*40,\s*0\.18\)/);

    expect(ideGuide).toMatch(
      /\.center-workbench__ide-guide--failure:has\(\.center-workbench__ide-guide-action--secondary\)[\s\S]*border-color:\s*rgba\(140,\s*190,\s*230,\s*0\.32\)/,
    );
  });

  it('loads conversation seam attachment styles from the mockup-shell aggregator chain', () => {
    const aggregator = readCss('mockup-shell.css');
    expect(aggregator).toMatch(
      /@import\s+['"]\.\/shell\/mockup-shell-25\.css['"]/,
    );

    const shell25 = readCss('shell/mockup-shell-25.css');
    const ide04 = readCss('ide/ide-layout-04.css');
    expect(shell25).toMatch(
      /@import\s+['"]\.\/conversation-seam-attachments\.css['"]/,
    );
    expect(shell25).not.toMatch(/\.conversation-seam__attachment-card\s*\{/);
    expect(ide04).not.toMatch(/\.conversation-seam__attachment-card\s*\{/);

    const attachments = readCss('shell/conversation-seam-attachments.css');
    const card = ruleBlock(attachments, '.conversation-seam__attachment-card');
    expect(card).toMatch(/cursor:\s*pointer/);

    const focus = ruleBlock(attachments, '.conversation-seam__attachment-card:focus-visible');
    expect(focus).toMatch(/outline:\s*2px solid rgba\(0,\s*242,\s*255,\s*0\.72\)/);

    const threadCard = ruleBlock(attachments, '.conversation-seam__attachment-card--thread');
    expect(threadCard).toMatch(/width:\s*2\.75rem/);
    expect(threadCard).toMatch(/height:\s*2\.75rem/);
  });

  it('tightens thread attachment cards inside the IDE agent dock transcript', () => {
    const ide04 = readCss('ide/ide-layout-04.css');
    const transcriptCard = ruleBlock(
      ide04,
      '.agent-dock__transcript .conversation-seam__attachment-card--thread',
    );
    expect(transcriptCard).toMatch(/width:\s*2\.75rem/);
    expect(transcriptCard).toMatch(/height:\s*2\.75rem/);

    const transcriptFileCard = ruleBlock(
      ide04,
      '.agent-dock__transcript .conversation-seam__attachment-card--thread.conversation-seam__attachment-card--file',
    );
    expect(transcriptFileCard).toMatch(/max-width:\s*6\.5rem/);
  });

  it('loads company roster alert styles from the mockup-shell aggregator', () => {
    const aggregator = readCss('mockup-shell.css');
    expect(aggregator).toMatch(/@import\s+['"]\.\/shell\/mockup-shell-tail\.css['"]/);

    const tail = readCss('shell/mockup-shell-tail.css');
    expect(tail).toMatch(/@import\s+['"]\.\/mockup-shell-32\.css['"]/);
    expect(tail).toMatch(/@import\s+['"]\.\/mockup-shell-33\.css['"]/);

    const shell32 = readCss('shell/mockup-shell-32.css');
    expect(shell32).toMatch(/@import\s+['"]\.\/company-roster-alert\.css['"]/);
    expect(shell32).not.toMatch(/\.company-roster__alert-badge\s*\{/);

    const rosterAlert = readCss('shell/company-roster-alert.css');
    const badge = ruleBlock(rosterAlert, '.company-roster__alert-badge');
    expect(badge).toMatch(/cursor:\s*pointer/);
    expect(badge).toMatch(/border:\s*1px solid rgba\(190,\s*80,\s*60,\s*0\.42\)/);

    const badgeFocus = ruleBlock(rosterAlert, '.company-roster__alert-badge:focus-visible');
    expect(badgeFocus).toMatch(/outline:\s*2px solid rgba\(220,\s*110,\s*90,\s*0\.55\)/);
    expect(badgeFocus).toMatch(/outline-offset:\s*2px/);

    const interruptedFocus = ruleBlock(
      rosterAlert,
      '.company-roster__alert-badge--interrupted:focus-visible',
    );
    expect(interruptedFocus).toMatch(/outline:\s*2px solid rgba\(255,\s*200,\s*110,\s*0\.55\)/);

    const mixedFocus = ruleBlock(
      rosterAlert,
      '.company-roster__alert-badge--mixed:focus-visible',
    );
    expect(mixedFocus).toMatch(/outline:\s*2px solid rgba\(255,\s*170,\s*120,\s*0\.55\)/);

    const hintActionFocus = ruleBlock(
      rosterAlert,
      '.company-roster__hint--action:focus-visible',
    );
    expect(hintActionFocus).toMatch(/outline:\s*2px solid rgba\(220,\s*110,\s*90,\s*0\.55\)/);
    expect(hintActionFocus).toMatch(/outline-offset:\s*2px/);

    const hintAlert = ruleBlock(rosterAlert, '.company-roster__hint--alert');
    expect(hintAlert).toMatch(/border:\s*1px solid rgba\(190,\s*80,\s*60,\s*0\.32\)/);
  });

  it('keeps the TEAM header fixed and makes the persona dock the sole vertical scroller', () => {
    const shell32 = readCss('shell/mockup-shell-32.css');
    const teamScroll = readCss('shell/mockup-shell-team-scroll.css');
    const roster = ruleBlock(shell32, '.company-roster--ide');
    const teamBody = ruleBlock(shell32, '.ide-team-panel__body');
    const dock = ruleBlock(teamScroll, '.company-roster--ide .company-roster__dock-host');
    const persona = ruleBlock(
      teamScroll,
      '.company-roster--ide .agent-persona-dock,\n.console-shell--mockup.console-shell--glass3d .ide-team-panel .agent-persona-dock',
    );

    expect(roster).toMatch(/overflow:\s*hidden/);
    expect(teamBody).toMatch(/overflow:\s*hidden/);
    expect(dock).toMatch(/max-height:\s*100%/);
    expect(dock).toMatch(/min-height:\s*0/);
    expect(dock).toMatch(/scrollbar-gutter:\s*stable/);
    expect(persona).toMatch(/min-height:\s*0/);
  });

  it('loads composer file attachment styles from the ide-layout aggregator', () => {
    const aggregator = readCss('ide-layout.css');
    expect(aggregator).toMatch(/@import\s+['"]\.\/ide\/ide-layout-07\.css['"]/);

    const layout06 = readCss('ide/ide-layout-06.css');
    const layout07 = readCss('ide/ide-layout-07.css');
    expect(layout06).toMatch(/\.agent-dock-composer__image-card\s*\{/);
    expect(layout07).not.toMatch(/\.agent-dock-composer__image-card\s*\{/);
    expect(layout07).toMatch(/\.agent-dock-composer__image-card--file/);

    const fileExt = ruleBlock(layout07, '.agent-dock-composer__file-ext');
    expect(fileExt).toMatch(/font-weight:\s*700/);

    const fileName = ruleBlock(layout07, '.agent-dock-composer__file-name');
    expect(fileName).toMatch(/-webkit-line-clamp:\s*[12]/);
  });
});
