import { describe, expect, it } from 'vitest';

import {
  agentContentHasTranscriptBlocks,
  diffLineTone,
  editedFilePathsFromTranscript,
  parseAgentTranscriptBlocks,
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

  it('marks streaming research blocks as open', () => {
    const segments = parseAgentTranscriptBlocks(':::research react hooks');
    expect(segments).toEqual([
      { kind: 'research', query: 'react hooks', items: [], open: true },
    ]);
  });

  it('passes plain replies through as one text segment', () => {
    expect(agentContentHasTranscriptBlocks('Just a reply')).toBe(false);
    expect(parseAgentTranscriptBlocks('Just a reply')).toEqual([
      { kind: 'text', text: 'Just a reply' },
    ]);
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
});

describe('editedFilePathsFromTranscript', () => {
  it('extracts workspace-relative edited paths', () => {
    expect(editedFilePathsFromTranscript(SAMPLE)).toEqual(['README.md']);
    const absolute =
      ':::edit /home/edp/.cursor/projects/foo/README.md +1 -0\n+line\n:::\n';
    expect(editedFilePathsFromTranscript(absolute)).toEqual(['README.md']);
  });
});
