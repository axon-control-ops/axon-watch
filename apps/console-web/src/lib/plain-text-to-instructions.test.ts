import { describe, expect, it } from 'vitest';
import {
  plainTextToInstructionsMarkdown,
  projectInstructionsSections,
} from './plain-text-to-instructions';

describe('plainTextToInstructionsMarkdown', () => {
  it('keeps existing Instructions markdown unchanged', () => {
    const existing = '# Instructions\n\n## Goal\nAlready done.\n';
    expect(plainTextToInstructionsMarkdown(existing)).toBe(existing);
  });

  it('preserves the full source request and does not invent CI/agent steps', () => {
    const plain =
      'Plan to address all this - we need Axon-X to really match Cursor Plan mode, keep auto-resume after refresh, and fix Instructions so plain text becomes a full super prompt without cutting details. I never said anything about committing.';

    const markdown = plainTextToInstructionsMarkdown(plain);
    expect(markdown).toContain('# Instructions');
    expect(markdown).toContain('## Source request');
    expect(markdown).toContain(plain);
    expect(markdown).toMatch(/Committing/i);
    expect(markdown.toLowerCase()).not.toMatch(/existing ci \/ build notes/);
    expect(markdown.toLowerCase()).not.toMatch(/map detection, triage, fix/);
    expect(markdown.toLowerCase()).not.toMatch(/staffed agents/);
    expect(markdown.toLowerCase()).not.toMatch(/amend|desk-clearing|suggesting commits/);

    const sections = projectInstructionsSections(plain);
    expect(sections.sourceRequest).toBe(plain);
    expect(sections.goal.toLowerCase()).toContain('plan to address all this');
    expect(sections.goal.toLowerCase()).not.toMatch(/^plan\s*$/);
    expect(sections.outOfScope.some((item) => /commit/i.test(item))).toBe(true);
    expect(sections.steps.every((step) => !/ci \/ build|staffed agents/i.test(step))).toBe(
      true,
    );
  });

  it('uses explicit list lines as Steps and keeps multi-sentence scope', () => {
    const plain = [
      'Ship the Plan mode resume fix.',
      '',
      '- Create linked plan runs',
      '- Persist recovery markers for plan',
      '- Reattach after browser refresh',
    ].join('\n');

    const sections = projectInstructionsSections(plain);
    expect(sections.steps).toEqual([
      'Create linked plan runs',
      'Persist recovery markers for plan',
      'Reattach after browser refresh',
    ]);
    expect(sections.sourceRequest).toContain('Ship the Plan mode resume fix.');
    expect(sections.inScope.some((item) => /Create linked plan runs/i.test(item))).toBe(
      true,
    );
  });

  it('returns a blank template for empty input', () => {
    const markdown = plainTextToInstructionsMarkdown('   ');
    expect(markdown).toContain('# Instructions');
    expect(markdown).toContain('Describe the outcome in one sentence.');
    expect(markdown).toContain('## Source request');
  });
});
