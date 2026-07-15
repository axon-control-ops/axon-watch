import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const testDir = dirname(fileURLToPath(import.meta.url));
const srcRoot = resolve(testDir, '../..');

function readSource(relativePath: string): string {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8');
}

describe('safe action surface truth', () => {
  it('labels briefing actions as guidance and points approvals to Mission Control', () => {
    const source = readSource('components/BriefingPanel.vue');

    expect(source).toContain('Suggested actions · guidance only');
    expect(source).toContain('Open Mission Control to approve, reject, or resume a run.');
    expect(source).toContain('Pending approvals · act in Mission Control');
  });

  it('labels galaxy safe actions as guidance rather than buttons', () => {
    const source = readSource('features/brain-galaxy/GalaxyIntelligencePanel.vue');

    expect(source).toContain('Suggested actions · guidance only');
  });
});
