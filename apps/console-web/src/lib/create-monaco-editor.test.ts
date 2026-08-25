import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

import { describe, expect, it } from 'vitest';

const requireFromTest = createRequire(import.meta.url);

function workerImportsFromSource(): string[] {
  const source = readFileSync(new URL('./create-monaco-editor.ts', import.meta.url), 'utf8');
  return [...source.matchAll(/from\s+['"]([^'"]+\?worker)['"]/g)].map(
    (match) => match[1] ?? '',
  );
}

describe('monaco worker imports', () => {
  it('resolves every Vite worker import against the installed monaco package', () => {
    const workerImports = workerImportsFromSource();
    expect(workerImports).toEqual([
      'monaco-editor/esm/vs/editor/editor.worker.js?worker',
      'monaco-editor/esm/vs/language/css/css.worker.js?worker',
      'monaco-editor/esm/vs/language/html/html.worker.js?worker',
      'monaco-editor/esm/vs/language/json/json.worker.js?worker',
      'monaco-editor/esm/vs/language/typescript/ts.worker.js?worker',
    ]);

    for (const workerImport of workerImports) {
      const modulePath = workerImport.replace(/\?worker$/, '');
      expect(requireFromTest.resolve(modulePath)).toMatch(/monaco-editor\/esm\/vs\/.+\.worker\.js$/);
    }
  });
});
