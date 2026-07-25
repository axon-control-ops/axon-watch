import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect } from 'vitest';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../styles');

export function readCss(relativePath: string): string {
  return readFileSync(resolve(ROOT, relativePath), 'utf8');
}

export function ruleBlock(css: string, selector: string): string {
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
