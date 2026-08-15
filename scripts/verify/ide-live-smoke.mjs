#!/usr/bin/env node
/**
 * Live IDE smoke — Playwright checks against a running console-web instance.
 * Usage: node scripts/verify/ide-live-smoke.mjs [--port 5173]
 */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const port = process.argv.includes('--port')
  ? process.argv[process.argv.indexOf('--port') + 1]
  : process.env.AXON_WATCH_CONSOLE_WEB_PORT ?? '5173';
const baseUrl = `http://127.0.0.1:${port}`;
const outDir = join(dirname(fileURLToPath(import.meta.url)), '../../.local/verify/ide-live-smoke');
mkdirSync(outDir, { recursive: true });

const checks = [];

function record(step, ok, detail = '') {
  checks.push({ step, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${step}${detail ? `: ${detail}` : ''}`);
}

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.addInitScript(() => {
    sessionStorage.setItem('axon-x-boot-complete', '1');
  });

  const res = await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  record('http_boot', res?.ok() === true, `HTTP ${res?.status() ?? 'none'}`);

  await page.waitForSelector('.console-shell--mockup', { timeout: 30000 });
  record('shell_render', true);

  const layout = page.getByRole('group', { name: 'Layout mode' });
  await layout.getByRole('button', { name: 'IDE', exact: true }).click();
  await page.waitForSelector('.console-shell--ide', { timeout: 15000 });
  record('ide_mode', true);

  const emptyEditor = page.locator('.center-workbench__empty-editor');
  const hasEmptyGuide = (await emptyEditor.count()) > 0;
  const hasEditor = (await page.locator('.surface-host--mockup').count()) > 0;
  record(
    'empty_editor_or_file_open',
    hasEmptyGuide || hasEditor,
    hasEmptyGuide ? 'empty editor guide visible' : 'editor tab open',
  );

  const reopen = page.locator('.agent-dock-reopen');
  if ((await reopen.count()) > 0) {
    await reopen.first().click();
  }
  await page.waitForSelector('.agent-dock-composer', { timeout: 15000 });
  record('agent_dock', true);

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  await page.waitForTimeout(2000);

  const ingestErrors = consoleErrors.filter((t) =>
    t.includes('7706/ingest') || t.includes('ERR_CONNECTION_REFUSED'),
  );
  record(
    'no_debug_ingest_errors',
    ingestErrors.length === 0,
    ingestErrors.length ? `${ingestErrors.length} ingest/refused errors` : 'clean',
  );

  const threeErrors = consoleErrors.filter((t) =>
    t.toLowerCase().includes('clearcolor') || t.toLowerCase().includes('clearalpha'),
  );
  record(
    'no_three_clearcolor_errors',
    threeErrors.length === 0,
    threeErrors.length ? threeErrors[0]?.slice(0, 120) : 'clean',
  );

  await page.screenshot({ path: join(outDir, 'ide-live-smoke.png'), fullPage: false });

  const failed = checks.filter((c) => !c.ok);
  const report = {
    generated_at: new Date().toISOString(),
    baseUrl,
    checks,
    console_error_count: consoleErrors.length,
    console_errors_sample: consoleErrors.slice(0, 8),
  };
  writeFileSync(join(outDir, 'ide-live-smoke-report.json'), `${JSON.stringify(report, null, 2)}\n`);

  if (failed.length) {
    console.error(`IDE-LIVE-SMOKE FAIL: ${failed.map((f) => f.step).join(', ')}`);
    process.exit(1);
  }
  console.log(`IDE-LIVE-SMOKE PASS (${checks.length} checks) — ${baseUrl}`);
} catch (error) {
  console.error(`IDE-LIVE-SMOKE FAIL: ${error instanceof Error ? error.message : error}`);
  process.exit(1);
} finally {
  await browser?.close();
}
