import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { readCss } from './css-layout-contract-helpers';

const CONSOLE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const REPO_ROOT = resolve(CONSOLE_ROOT, '../..');

describe('operator console stability guardrails', () => {
  it('loads IDE motion guardrails after all feature styles', () => {
    const appCss = readCss('app.css');
    const settingsImport = appCss.indexOf("@import './settings-surface.css';");
    const guardrailImport = appCss.indexOf("@import './ide-motion-guardrails.css';");
    expect(guardrailImport).toBeGreaterThan(settingsImport);
  });

  it('disables persistent decorative IDE motion without disabling progress spinners', () => {
    const css = readCss('ide-motion-guardrails.css');
    expect(css).toContain("[class*='pulse']");
    expect(css).toContain("[class*='attention']");
    expect(css).toContain("[class*='streaming']");
    expect(css).toMatch(/animation:\s*none !important/);
    expect(css).not.toContain('spinner');
  });

  it('makes Vite HMR opt-in and revive stops the edit server', () => {
    const viteConfig = readFileSync(resolve(CONSOLE_ROOT, 'vite.config.ts'), 'utf8');
    expect(viteConfig).toContain("process.env.AXON_WATCH_VITE_HMR === '1'");
    expect(viteConfig).toContain('hmr: hmrEnabled');

    const revive = readFileSync(resolve(REPO_ROOT, 'scripts/ops/axonrevive.sh'), 'utf8');
    expect(revive).toContain("pkill -f 'vite --host 127\\.0\\.0\\.1 --port 5173'");
  });

  it('coalesces ResizeObserver layout writes outside the observer callback', () => {
    const workbench = readFileSync(
      resolve(CONSOLE_ROOT, 'src/components/shell/CenterWorkbench.vue'),
      'utf8',
    );
    expect(workbench).toContain('function scheduleResizeLayoutSync()');
    expect(workbench).toMatch(
      /new ResizeObserver\(\(\) => \{[\s\S]*?scheduleResizeLayoutSync\(\);[\s\S]*?\}\)/,
    );
    expect(workbench).not.toMatch(
      /new ResizeObserver\(\(\) => \{\s*runLayoutSync\('resize'\);\s*\}\)/,
    );
  });
});
