import { describe, expect, it } from 'vitest';

import {
  composerDraftIncludesToken,
  resolveComposerContextPayload,
  SELECTION_CONTEXT_TOKEN,
  TERMINAL_CONTEXT_TOKEN,
  truncateContextSnippet,
} from './ide-composer-context-tokens';

describe('ide composer context tokens', () => {
  it('detects context tokens on their own lines', () => {
    const draft = `${SELECTION_CONTEXT_TOKEN}\nExplain this block`;
    expect(composerDraftIncludesToken(draft, SELECTION_CONTEXT_TOKEN)).toBe(true);
    expect(composerDraftIncludesToken(draft, TERMINAL_CONTEXT_TOKEN)).toBe(false);
  });

  it('builds selection and terminal payloads only when tokens are present', () => {
    const draft = `${SELECTION_CONTEXT_TOKEN}\n${TERMINAL_CONTEXT_TOKEN}\nFix the failing test`;
    const payload = resolveComposerContextPayload({
      draft,
      workspaceId: 'workspace_axon_watch',
      activeFilePath: 'src/app.ts',
      editorSelection: {
        startLine: 4,
        endLine: 6,
        text: 'const answer = 42;',
      },
    });

    expect(payload.editor_selection).toEqual({
      file_path: 'src/app.ts',
      start_line: 4,
      end_line: 6,
      text: 'const answer = 42;',
    });
    expect(payload.terminal_snippet).toBeNull();
  });

  it('truncates oversized snippets', () => {
    const long = 'x'.repeat(5000);
    expect(truncateContextSnippet(long, 100).length).toBeLessThanOrEqual(100);
    expect(truncateContextSnippet(long, 100).endsWith('…')).toBe(true);
  });
});
