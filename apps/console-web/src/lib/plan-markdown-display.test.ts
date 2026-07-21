import { describe, expect, it } from 'vitest';

import { sanitizePlanMarkdownForDisplay } from './plan-markdown-display';

describe('sanitizePlanMarkdownForDisplay', () => {
  it('strips research fences and leading process narration', () => {
    const raw = `# Centre brief

I'll review the local planning docs first.

:::research Web search
@kind search
:::

## Goal
Open the aftercare centre safely.

## Steps
1. Confirm ages
2. Confirm hours
3. Confirm ratios
`;
    const cleaned = sanitizePlanMarkdownForDisplay(raw);
    expect(cleaned).not.toContain(':::research');
    expect(cleaned).not.toContain("I'll review");
    expect(cleaned).toContain('## Goal');
    expect(cleaned.startsWith('# Centre brief')).toBe(true);
  });

  it('cleans the duplicate-title shape emitted by a researched Plan turn', () => {
    const raw = `# School plan

Axon research is ready. Next I'll pull local pricing benchmarks.

# School plan

## Goal
Open the centre safely.
`;
    const cleaned = sanitizePlanMarkdownForDisplay(raw);
    expect(cleaned).toBe(`# School plan

## Goal
Open the centre safely.`);
  });

  it('drops an unclosed noisy fence at end of content', () => {
    const raw = `# Centre brief

## Goal
Open safely.

:::research Web search
unfinished tool output`;
    const cleaned = sanitizePlanMarkdownForDisplay(raw);
    expect(cleaned).toBe(`# Centre brief

## Goal
Open safely.`);
  });
});
