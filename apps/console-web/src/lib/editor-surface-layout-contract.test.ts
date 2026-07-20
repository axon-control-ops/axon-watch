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
});
