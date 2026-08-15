import { describe, expect, it } from 'vitest';

import {
  agentContentHasTranscriptBlocks,
  collapseClosedEditSegmentsForDisplay,
  diffLineTone,
  editedFilePathsFromTranscript,
  normalizeEditedFilePath,
  parseAgentTranscriptBlocks,
  prepareAgentTranscriptSegmentsForDisplay,
  thinkingPreview,
} from './agent-transcript-blocks';

const SAMPLE = [
  "I'll update the README now.",
  '',
  ':::thinking',
  'Line 2 is blank. Insert an HTML comment there.',
  ':::',
  '',
  ':::tool Read README.md',
  '',
  ':::edit README.md +1 -0',
  '--- a/README.md',
  '+++ b/README.md',
  '@@ -1,3 +1,4 @@',
  ' # Test',
  '+<!-- Agent is working -->',
  ':::',
  '',
  'DONE',
].join('\n');

describe('parseAgentTranscriptBlocks', () => {
  it('parses durable plan fences as View Plan segments', () => {
    const content = [
      '# Soft cutover',
      '',
      '1. Proxy public origin',
      '',
      ':::plan plan_abcdef123456 Soft cutover',
      ':::',
    ].join('\n');
    expect(agentContentHasTranscriptBlocks(content)).toBe(true);
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments.map((segment) => segment.kind)).toEqual(['text', 'plan']);
    const plan = segments[1];
    expect(plan.kind).toBe('plan');
    if (plan.kind === 'plan') {
      expect(plan.planId).toBe('plan_abcdef123456');
      expect(plan.title).toBe('Soft cutover');
    }
  });

  it('parses debug reproduce steps as a dedicated segment', () => {
    const content = [
      'Instrumentation is ready.',
      ':::debug-reproduce',
      '1. Open the settings panel',
      '2. Click Save',
      ':::',
    ].join('\n');
    expect(agentContentHasTranscriptBlocks(content)).toBe(true);
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments.map((segment) => segment.kind)).toEqual(['text', 'debug-reproduce']);
    const reproduce = segments[1];
    expect(reproduce.kind).toBe('debug-reproduce');
    if (reproduce.kind === 'debug-reproduce') {
      expect(reproduce.steps).toEqual(['Open the settings panel', 'Click Save']);
      expect(reproduce.open).toBe(false);
    }
  });

  it('splits text, thinking, tool, and edit segments in order', () => {
    const segments = parseAgentTranscriptBlocks(SAMPLE);
    expect(segments.map((segment) => segment.kind)).toEqual([
      'text',
      'thinking',
      'tool',
      'edit',
      'text',
    ]);
    const edit = segments[3];
    if (edit.kind !== 'edit') throw new Error('expected edit segment');
    expect(edit.path).toBe('README.md');
    expect(edit.added).toBe(1);
    expect(edit.removed).toBe(0);
    expect(edit.diff).toContain('+<!-- Agent is working -->');
    expect(edit.open).toBe(false);
  });

  it('marks unterminated blocks as open during streaming', () => {
    const segments = parseAgentTranscriptBlocks(':::thinking\nStill reasoning');
    expect(segments).toEqual([{ kind: 'thinking', text: 'Still reasoning', open: true }]);
  });

  it('parses terminal blocks with command and output', () => {
    const content = [
      ':::terminal npm test',
      '> vitest run',
      'Tests 227 passed',
      ':::',
    ].join('\n');
    expect(agentContentHasTranscriptBlocks(content)).toBe(true);
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments).toEqual([
      {
        kind: 'terminal',
        command: 'npm test',
        output: '> vitest run\nTests 227 passed',
        open: false,
      },
    ]);
  });

  it('sanitizes jest ansi noise from terminal transcript blocks', () => {
    const noisy = [
      ':::terminal npm test',
      '\x1b[1A\x1b[2K\x1b[32mPASS\x1b[0m tests/unit/foo.test.ts',
      '[1A[2K[32mPASS[0m tests/unit/bar.test.ts',
      'Test Suites: 2 passed, 2 total',
      ':::',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(noisy);
    const terminal = segments[0];
    expect(terminal?.kind).toBe('terminal');
    if (terminal?.kind !== 'terminal') throw new Error('expected terminal segment');
    expect(terminal.output).not.toMatch(/\x1b\[/);
    expect(terminal.output).not.toMatch(/\[1A/);
    expect(terminal.output).toContain('PASS');
    expect(terminal.output).toContain('Test Suites: 2 passed, 2 total');
  });

  it('compacts legacy oversized terminal output before rendering', () => {
    const output = `HEAD\n${'x'.repeat(30_000)}\nTAIL`;
    const segments = parseAgentTranscriptBlocks(
      [':::terminal cat big.log', output, ':::'].join('\n'),
    );
    const terminal = segments[0];
    expect(terminal?.kind).toBe('terminal');
    if (terminal?.kind !== 'terminal') throw new Error('expected terminal segment');
    expect(terminal.output).toContain('HEAD');
    expect(terminal.output).toContain('TAIL');
    expect(terminal.output).toContain('characters compacted to keep the IDE responsive');
    expect(terminal.output.length).toBeLessThan(16_000);
  });

  it('marks streaming terminal blocks as open', () => {
    const segments = parseAgentTranscriptBlocks(':::terminal git status');
    expect(segments).toEqual([
      { kind: 'terminal', command: 'git status', output: '', open: true },
    ]);
  });

  it('parses research cards with query, sources, and snippets', () => {
    const content = [
      ':::research vite configuration',
      '- Vite Guide | https://vitejs.dev/guide/',
      'Official Vite documentation.',
      '- Rollup options | https://rollupjs.org/',
      'Bundler reference.',
      ':::',
    ].join('\n');
    expect(agentContentHasTranscriptBlocks(content)).toBe(true);
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments).toEqual([
      {
        kind: 'research',
        query: 'vite configuration',
        items: [
          {
            title: 'Vite Guide',
            url: 'https://vitejs.dev/guide/',
            snippet: 'Official Vite documentation.',
          },
          {
            title: 'Rollup options',
            url: 'https://rollupjs.org/',
            snippet: 'Bundler reference.',
          },
        ],
        open: false,
      },
    ]);
  });

  it('parses provider and kind metadata on research blocks', () => {
    const content = [
      ':::research react hooks',
      '@kind search',
      '@provider duckduckgo_instant',
      '- React docs | https://react.dev/',
      'Hooks reference.',
      ':::',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments).toEqual([
      {
        kind: 'research',
        query: 'react hooks',
        provider: 'duckduckgo_instant',
        kindLabel: 'search',
        items: [
          {
            title: 'React docs',
            url: 'https://react.dev/',
            snippet: 'Hooks reference.',
          },
        ],
        open: false,
      },
    ]);
  });

  it('infers research kind from query label when metadata is absent', () => {
    const segments = parseAgentTranscriptBlocks(':::research Page fetch\n- docs | https://example.com\n:::');
    const block = segments[0];
    if (block.kind !== 'research') throw new Error('expected research');
    expect(block.kindLabel).toBe('fetch');
  });

  it('dedupes duplicate prose after thinking blocks', () => {
    const line =
      'Running the August billing dry-run and verifying deployment state from the prior session.';
    const content = [
      ':::thinking',
      'Planning next steps.',
      ':::',
      line,
      line,
      '',
      ':::tool Read scripts/backfill.ts',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments.map((segment) => segment.kind)).toEqual(['thinking', 'text', 'tool']);
    const prose = segments[1];
    if (prose.kind !== 'text') throw new Error('expected text segment');
    expect(prose.text).toBe(line);
  });

  it('collapses glued partial Day-to-day section echoes in AgentDock prose', () => {
    const opener =
      'No — that “Working with …” starter line does not need to sit in the composer. ' +
      'Talk already introduces the teammate. The composer should stay clear for the real ask.';
    const changed = [
      '**What I changed**',
      '- Clicking **Talk** opens chat without stuffing a boilerplate sentence.',
      '- **Status** and **Assign** still prefill useful prompts.',
    ].join('\n');
    const dayToDay = [
      '**Day-to-day with Agents**',
      '1. Open **Team** in the left bar — each person owns a slice of the business.',
      '2. Working agents **glow**; they can **speak** a short status when you engage them.',
      '3. Click a teammate, then type what you need in the composer.',
      '4. Approve when Full Access asks; watch the dock for progress and handoffs.',
      '5. Lead for priorities, Night Watch for signals/health — that is the daily loop.',
    ].join('\n');
    // Real Cursor shape: echo skips the middle "What I changed" section.
    const content = [
      ':::thinking',
      'Answer both questions.',
      ':::',
      `${opener}\n\n${changed}\n\n${dayToDay}${opener}\n\n${dayToDay}`,
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    const prose = segments.find((segment) => segment.kind === 'text');
    expect(prose?.kind).toBe('text');
    if (prose?.kind !== 'text') throw new Error('expected text segment');
    expect(prose.text.match(/Day-to-day with Agents/g)?.length ?? 0).toBe(1);
    expect(prose.text.match(/No —/g)?.length ?? 0).toBe(1);
    expect(prose.text).toContain('What I changed');
    expect(prose.text.trim().endsWith('daily loop.')).toBe(true);
  });

  it('merges adjacent duplicate research segments', () => {
    const content = [
      ':::research vite configuration',
      '- Vite Guide | https://vitejs.dev/guide/',
      ':::',
      ':::research vite configuration',
      '- Rollup | https://rollupjs.org/',
      ':::',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments).toEqual([
      {
        kind: 'research',
        query: 'vite configuration',
        items: [
          {
            title: 'Vite Guide',
            url: 'https://vitejs.dev/guide/',
            snippet: '',
          },
          {
            title: 'Rollup',
            url: 'https://rollupjs.org/',
            snippet: '',
          },
        ],
        open: false,
      },
    ]);
  });

  it('drops repeated prose across tool blocks', () => {
    const content = [
      'Here is the answer.',
      '',
      ':::tool Read README.md',
      '',
      'Here is the answer.',
      '',
      'More details.',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments.map((segment) => segment.kind)).toEqual(['text', 'tool', 'text']);
    const intro = segments[0];
    const outro = segments[2];
    if (intro.kind !== 'text' || outro.kind !== 'text') {
      throw new Error('expected text segments');
    }
    expect(intro.text).toBe('Here is the answer.');
    expect(outro.text).toBe('More details.');
  });

  it('passes plain replies through as one text segment', () => {
    expect(agentContentHasTranscriptBlocks('Just a reply')).toBe(false);
    expect(parseAgentTranscriptBlocks('Just a reply')).toEqual([
      { kind: 'text', text: 'Just a reply' },
    ]);
  });

  it('parses edit-failed fences and legacy tool labels', () => {
    const content = [
      ':::edit-failed tests/test_foo.py',
      'Sandbox policy denied write to tests/test_foo.py',
      ':::',
      '',
      ':::tool Edit failed scripts/workflow/foo.mjs',
    ].join('\n');
    const segments = parseAgentTranscriptBlocks(content);
    expect(segments[0]).toEqual({
      kind: 'edit-failed',
      path: 'tests/test_foo.py',
      reason: 'Sandbox policy denied write to tests/test_foo.py',
    });
    expect(segments[1]).toEqual({
      kind: 'edit-failed',
      path: 'scripts/workflow/foo.mjs',
      reason: 'Edit was rejected (path may be outside write scope or patch did not apply).',
    });
    expect(agentContentHasTranscriptBlocks(content)).toBe(true);
  });
});

describe('diffLineTone', () => {
  it('classifies diff lines', () => {
    expect(diffLineTone('+++ b/x')).toBe('meta');
    expect(diffLineTone('@@ -1 +1 @@')).toBe('meta');
    expect(diffLineTone('+added')).toBe('add');
    expect(diffLineTone('-removed')).toBe('remove');
    expect(diffLineTone(' context')).toBe('context');
  });
});

describe('thinkingPreview', () => {
  it('flattens and truncates long reasoning', () => {
    expect(thinkingPreview('short thought')).toBe('short thought');
    const long = 'word '.repeat(40);
    expect(thinkingPreview(long).length).toBeLessThanOrEqual(90);
    expect(thinkingPreview(long).endsWith('…')).toBe(true);
  });

  it('replaces pure user-meta thinking with Working…', () => {
    expect(thinkingPreview('The user is asking whether')).toBe('Working…');
  });
});

describe('editedFilePathsFromTranscript', () => {
  it('extracts workspace-relative edited paths', () => {
    expect(editedFilePathsFromTranscript(SAMPLE)).toEqual(['README.md']);
    const absolute =
      ':::edit /home/edp/.cursor/projects/foo/README.md +1 -0\n+line\n:::\n';
    expect(editedFilePathsFromTranscript(absolute)).toEqual(['README.md']);
  });
});

describe('normalizeEditedFilePath', () => {
  it('keeps workspace-relative paths', () => {
    expect(normalizeEditedFilePath('apps/console-web/src/App.vue')).toBe(
      'apps/console-web/src/App.vue',
    );
  });

  it('maps absolute paths to their file name', () => {
    expect(
      normalizeEditedFilePath('/home/edp/.cursor/projects/foo/README.md'),
    ).toBe('README.md');
  });
});

describe('collapseClosedEditSegmentsForDisplay', () => {
  it('collapses large closed-edit fan-out into a single summary chip', () => {
    const segments = Array.from({ length: 20 }, (_, index) => ({
      kind: 'edit' as const,
      path: `file-${index}.ts`,
      added: 1,
      removed: 0,
      diff: `+line ${index}`,
      open: false,
    }));
    segments.push({
      kind: 'edit',
      path: 'still-open.ts',
      added: 1,
      removed: 0,
      diff: '+live',
      open: true,
    });

    const collapsed = collapseClosedEditSegmentsForDisplay(segments, 8);
    expect(collapsed).toEqual([
      { kind: 'tool', label: 'Updated 20 files' },
      {
        kind: 'edit',
        path: 'still-open.ts',
        added: 1,
        removed: 0,
        diff: '+live',
        open: true,
      },
    ]);
  });

  it('is used by the conversation display helper', () => {
    const content = Array.from({ length: 12 }, (_, index) =>
      [`:::edit file-${index}.ts +1 -0`, `+x`, `:::`].join('\n'),
    ).join('\n');
    const segments = prepareAgentTranscriptSegmentsForDisplay(content, {
      collapseClosedEditsAt: 8,
    });
    expect(segments).toEqual([{ kind: 'tool', label: 'Updated 12 files' }]);
  });
});
