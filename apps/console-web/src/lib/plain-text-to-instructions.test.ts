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

  it('builds concise sections from a plain DashPro CI request', () => {
    const plain =
      'Look at what Dashpro workspace said about the CI work and plan how the Agents we have built would handle that. I never said anything about committing. Also fix how you take instruction — turn plain text into Instructions markdown with concise precise steps.';

    const markdown = plainTextToInstructionsMarkdown(plain);
    expect(markdown).toContain('# Instructions');
    expect(markdown).toContain('## Goal');
    expect(markdown).toContain('## Out of scope');
    expect(markdown).toMatch(/Committing/i);
    expect(markdown).toContain('## Steps');
    expect(markdown).toMatch(/1\.\s+/);
    expect(markdown.toLowerCase()).not.toMatch(/clear the local desk/);

    const sections = projectInstructionsSections(plain);
    expect(sections.goal.toLowerCase()).toMatch(/ci|agents|plan|review/);
    expect(sections.outOfScope.some((item) => /commit/i.test(item))).toBe(true);
    expect(sections.constraints.some((item) => /not invent/i.test(item))).toBe(true);
  });

  it('returns a blank template for empty input', () => {
    const markdown = plainTextToInstructionsMarkdown('   ');
    expect(markdown).toContain('# Instructions');
    expect(markdown).toContain('Describe the outcome in one sentence.');
  });
});
