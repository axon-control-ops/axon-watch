import { describe, expect, it } from 'vitest';

import {
  buildIdeGitPanelCaption,
  buildIdeSearchPanelCaption,
  countIdeDirtyFileTabs,
  ideActivityPanelCollapseAriaLabel,
  ideGitPanelCaptionUsesLiveRegion,
  ideGitPanelListAriaLabel,
  ideSearchPanelRetryAriaLabel,
  clampIdeSearchPanelHighlightIndex,
  resolveIdeGitPanelEnterDocumentId,
  resolveIdeSearchPanelEnterPath,
  resolveIdeSearchPanelEscapeAction,
  stepIdeSearchPanelHighlightIndex,
  shouldShowIdeGitPanelList,
  shouldShowIdeSearchPanelResults,
  shouldShowIdeSearchPanelRetry,
  shouldShowIdeSearchPanelAttention,
  ideSearchPanelCaptionUsesLiveRegion,
  ideSearchPanelResultsAriaLabel,
} from './ide-activity-panel-view';

describe('ideActivityPanelCollapseAriaLabel', () => {
  it('names each sidebar panel collapse control', () => {
    expect(ideActivityPanelCollapseAriaLabel('explorer')).toBe('Collapse explorer panel');
    expect(ideActivityPanelCollapseAriaLabel('search')).toBe('Collapse search panel');
    expect(ideActivityPanelCollapseAriaLabel('git')).toBe('Collapse source control panel');
    expect(ideActivityPanelCollapseAriaLabel('run')).toBe('Collapse run panel');
    expect(ideActivityPanelCollapseAriaLabel('team')).toBe('Collapse workspace team panel');
    expect(ideActivityPanelCollapseAriaLabel('agent')).toBe('Collapse agent panel');
    expect(ideActivityPanelCollapseAriaLabel('terminal')).toBe('Collapse terminal panel');
  });
});

describe('buildIdeSearchPanelCaption', () => {
  it('prompts to open a workspace when none is selected', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 0,
        loadState: 'loaded',
        hasWorkspace: false,
      }),
    ).toContain('Open a workspace');
  });

  it('shows loading copy while files are fetching', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 0,
        loadState: 'loading',
        hasWorkspace: true,
      }),
    ).toContain('Loading workspace files');
  });

  it('surfaces no-match guidance for active queries', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: 'missing.ts',
        resultCount: 0,
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe('No file paths match "missing.ts".');
  });

  it('returns null when a filtered query has matches', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: 'readme',
        resultCount: 2,
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBeNull();
  });

  it('prompts to filter when browsing an unfiltered file list', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 5,
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe('Type to filter workspace paths.');
  });

  it('surfaces error guidance when the file list fails to load', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 0,
        loadState: 'error',
        hasWorkspace: true,
      }),
    ).toContain('Could not load workspace files');
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 0,
        loadState: 'error',
        hasWorkspace: true,
      }),
    ).toContain('Retry below');
  });

  it('prompts when the workspace has no files yet', () => {
    expect(
      buildIdeSearchPanelCaption({
        query: '',
        resultCount: 0,
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe('No files in this workspace yet.');
  });
});

describe('buildIdeGitPanelCaption', () => {
  it('summarizes dirty file tabs when changes are pending', () => {
    expect(buildIdeGitPanelCaption(2)).toBe('2 file(s) with unsaved changes');
  });

  it('prompts when every tab is saved', () => {
    expect(buildIdeGitPanelCaption(0)).toBe('No unsaved files in the current workspace.');
  });
});

describe('countIdeDirtyFileTabs', () => {
  it('counts only dirty workspace file tabs', () => {
    expect(
      countIdeDirtyFileTabs([
        { source: 'file', dirty: true },
        { source: 'file', dirty: false },
        { source: 'scratch', dirty: true },
      ]),
    ).toBe(1);
  });
});

describe('shouldShowIdeGitPanelList', () => {
  it('lists dirty tabs only when at least one file is unsaved', () => {
    expect(shouldShowIdeGitPanelList(0)).toBe(false);
    expect(shouldShowIdeGitPanelList(1)).toBe(true);
  });
});

describe('ideGitPanelListAriaLabel', () => {
  it('names the unsaved-file list for screen readers', () => {
    expect(ideGitPanelListAriaLabel(1)).toBe('1 unsaved workspace file');
    expect(ideGitPanelListAriaLabel(3)).toBe('3 unsaved workspace files');
  });
});

describe('ideGitPanelCaptionUsesLiveRegion', () => {
  it('announces when unsaved files need attention', () => {
    expect(ideGitPanelCaptionUsesLiveRegion(1)).toBe(true);
    expect(ideGitPanelCaptionUsesLiveRegion(0)).toBe(false);
  });
});

describe('resolveIdeGitPanelEnterDocumentId', () => {
  it('opens the highlighted dirty tab when Enter is pressed', () => {
    expect(
      resolveIdeGitPanelEnterDocumentId({
        documents: [{ id: 'a' }, { id: 'b' }],
        listVisible: true,
        highlightIndex: 1,
      }),
    ).toBe('b');
  });

  it('returns null when the list is hidden or empty', () => {
    expect(
      resolveIdeGitPanelEnterDocumentId({
        documents: [{ id: 'a' }],
        listVisible: false,
      }),
    ).toBeNull();
    expect(
      resolveIdeGitPanelEnterDocumentId({
        documents: [],
        listVisible: true,
      }),
    ).toBeNull();
  });
});

describe('shouldShowIdeSearchPanelRetry', () => {
  it('offers retry only after a load error with an open workspace', () => {
    expect(
      shouldShowIdeSearchPanelRetry({
        loadState: 'error',
        hasWorkspace: true,
      }),
    ).toBe(true);
    expect(
      shouldShowIdeSearchPanelRetry({
        loadState: 'error',
        hasWorkspace: false,
      }),
    ).toBe(false);
    expect(
      shouldShowIdeSearchPanelRetry({
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe(false);
  });
});

describe('shouldShowIdeSearchPanelAttention', () => {
  it('matches retry visibility for load failures', () => {
    const input = { loadState: 'error' as const, hasWorkspace: true };
    expect(shouldShowIdeSearchPanelAttention(input)).toBe(true);
    expect(shouldShowIdeSearchPanelRetry(input)).toBe(true);
  });

  it('stays quiet while files are loading or loaded', () => {
    expect(
      shouldShowIdeSearchPanelAttention({
        loadState: 'loading',
        hasWorkspace: true,
      }),
    ).toBe(false);
    expect(
      shouldShowIdeSearchPanelAttention({
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe(false);
  });
});

describe('ideSearchPanelRetryAriaLabel', () => {
  it('names the retry control for idle and loading states', () => {
    expect(ideSearchPanelRetryAriaLabel(false)).toBe('Retry loading workspace files');
    expect(ideSearchPanelRetryAriaLabel(true)).toBe('Retrying workspace file load');
  });
});

describe('shouldShowIdeSearchPanelResults', () => {
  it('hides results until files finish loading', () => {
    expect(
      shouldShowIdeSearchPanelResults({
        resultCount: 3,
        loadState: 'loading',
        hasWorkspace: true,
      }),
    ).toBe(false);
  });

  it('hides stale rows after a load error', () => {
    expect(
      shouldShowIdeSearchPanelResults({
        resultCount: 3,
        loadState: 'error',
        hasWorkspace: true,
      }),
    ).toBe(false);
  });

  it('shows matches once the workspace file list is loaded', () => {
    expect(
      shouldShowIdeSearchPanelResults({
        resultCount: 2,
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe(true);
  });
});

describe('clampIdeSearchPanelHighlightIndex', () => {
  it('keeps the highlight inside the result list bounds', () => {
    expect(clampIdeSearchPanelHighlightIndex(2, 5)).toBe(2);
    expect(clampIdeSearchPanelHighlightIndex(9, 5)).toBe(4);
    expect(clampIdeSearchPanelHighlightIndex(-1, 5)).toBe(0);
    expect(clampIdeSearchPanelHighlightIndex(0, 0)).toBe(0);
  });
});

describe('stepIdeSearchPanelHighlightIndex', () => {
  it('wraps down and up through the result list', () => {
    expect(
      stepIdeSearchPanelHighlightIndex({
        currentIndex: 0,
        direction: 'down',
        resultCount: 3,
      }),
    ).toBe(1);
    expect(
      stepIdeSearchPanelHighlightIndex({
        currentIndex: 2,
        direction: 'down',
        resultCount: 3,
      }),
    ).toBe(0);
    expect(
      stepIdeSearchPanelHighlightIndex({
        currentIndex: 0,
        direction: 'up',
        resultCount: 3,
      }),
    ).toBe(2);
  });
});

describe('resolveIdeSearchPanelEnterPath', () => {
  it('opens the first visible result on Enter', () => {
    expect(
      resolveIdeSearchPanelEnterPath({
        results: [{ path: 'README.md' }, { path: 'notes.txt' }],
        resultsVisible: true,
      }),
    ).toBe('README.md');
  });

  it('opens the highlighted result when arrow keys moved the selection', () => {
    expect(
      resolveIdeSearchPanelEnterPath({
        results: [{ path: 'README.md' }, { path: 'notes.txt' }],
        resultsVisible: true,
        highlightIndex: 1,
      }),
    ).toBe('notes.txt');
  });

  it('stays inert while results are hidden or empty', () => {
    expect(
      resolveIdeSearchPanelEnterPath({
        results: [{ path: 'README.md' }],
        resultsVisible: false,
      }),
    ).toBeNull();
    expect(
      resolveIdeSearchPanelEnterPath({
        results: [],
        resultsVisible: true,
      }),
    ).toBeNull();
  });
});

describe('ideSearchPanelResultsAriaLabel', () => {
  it('names filtered matches with the active query', () => {
    expect(
      ideSearchPanelResultsAriaLabel({ resultCount: 2, query: 'readme' }),
    ).toBe('2 file paths matching "readme"');
    expect(
      ideSearchPanelResultsAriaLabel({ resultCount: 1, query: '  App.vue  ' }),
    ).toBe('1 file path matching "App.vue"');
  });

  it('names the default workspace path list when the query is blank', () => {
    expect(
      ideSearchPanelResultsAriaLabel({ resultCount: 24, query: '' }),
    ).toBe('24 workspace file paths');
  });
});

describe('ideSearchPanelCaptionUsesLiveRegion', () => {
  it('announces load failures when a workspace is open', () => {
    expect(
      ideSearchPanelCaptionUsesLiveRegion({
        loadState: 'error',
        hasWorkspace: true,
      }),
    ).toBe(true);
  });

  it('stays quiet while loading, healthy, or when no workspace is selected', () => {
    expect(
      ideSearchPanelCaptionUsesLiveRegion({
        loadState: 'error',
        hasWorkspace: false,
      }),
    ).toBe(false);
    expect(
      ideSearchPanelCaptionUsesLiveRegion({
        loadState: 'loaded',
        hasWorkspace: true,
      }),
    ).toBe(false);
    expect(
      ideSearchPanelCaptionUsesLiveRegion({
        loadState: 'loading',
        hasWorkspace: true,
      }),
    ).toBe(false);
  });
});

describe('resolveIdeSearchPanelEscapeAction', () => {
  it('clears an active query before collapsing the sidebar', () => {
    expect(resolveIdeSearchPanelEscapeAction('readme')).toBe('clear-query');
    expect(resolveIdeSearchPanelEscapeAction('  readme  ')).toBe('clear-query');
  });

  it('collapses when the query is blank', () => {
    expect(resolveIdeSearchPanelEscapeAction('')).toBe('collapse-panel');
    expect(resolveIdeSearchPanelEscapeAction('   ')).toBe('collapse-panel');
  });
});
