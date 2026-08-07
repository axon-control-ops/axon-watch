import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const srcRoot = resolve(import.meta.dirname, '../..');

function source(path: string): string {
  return readFileSync(resolve(srcRoot, path), 'utf8');
}

describe('company roster reporting layout', () => {
  it('keeps the team roster visible while a selected teammate streams a report', () => {
    const panel = source('components/shell/CompanyRosterPanel.vue');
    const reportingCss = source('styles/shell/agent-persona-dock-reporting.css');

    expect(panel).not.toContain("company-roster--reporting");
    expect(panel).not.toContain("company-roster__presence-strip--collapsed");
    expect(panel).not.toContain(':aria-hidden="selectedEmployeeIsReporting"');
    expect(panel).toContain(':reporting="selectedEmployeeIsReporting"');
    expect(reportingCss).not.toContain('max-height: 0');
    expect(reportingCss).toContain('max-height: min(22rem, 34vh)');
  });
});
