import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../styles');

function readCss(relativePath: string): string {
  return readFileSync(resolve(ROOT, relativePath), 'utf8');
}

function ruleBlock(css: string, selector: string): string {
  // Prefer an exact selector token so `.foo` does not match `.foobar`.
  const exact = new RegExp(
    `(^|[\\s}])${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{`,
    'm',
  );
  const match = exact.exec(css);
  expect(match, `missing selector ${selector}`).toBeTruthy();
  const open = css.indexOf('{', match!.index);
  const close = css.indexOf('}', open);
  expect(close).toBeGreaterThan(open);
  return css.slice(open + 1, close);
}

describe('IDE editor surface layout contract', () => {
  it('keeps Monaco editor host relative (EditContext-safe; do not absolute-collapse)', () => {
    const css = readCss('shell/mockup-shell-07.css');
    const body = ruleBlock(css, '.center-workbench__editor .surface-host__body--editor');
    expect(body).toMatch(/position:\s*relative/);
    expect(body).toMatch(/isolation:\s*isolate/);

    const frame = ruleBlock(css, '.center-workbench__editor .surface-host__frame--editor');
    expect(frame).toMatch(/position:\s*relative/);
    expect(frame).not.toMatch(/position:\s*absolute/);
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
  });

  it('loads connector attention pulse styles from the ide-layout aggregator', () => {
    const aggregator = readCss('ide-layout.css');
    expect(aggregator).toMatch(
      /@import\s+['"]\.\/ide\/ide-layout-01-connector-attention\.css['"]/,
    );

    const layout01 = readCss('ide/ide-layout-01.css');
    expect(layout01).not.toMatch(/ide-activity-bar-pulse-warning/);

    const connectorAttention = readCss('ide/ide-layout-01-connector-attention.css');
    const warningPulse = ruleBlock(connectorAttention, '.ide-activity-bar__pulse--warning');
    expect(warningPulse).toMatch(/animation:\s*ide-activity-bar-pulse-warning/);
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
    expect(threadCard).toMatch(/max-height:\s*14rem/);
  });
});
