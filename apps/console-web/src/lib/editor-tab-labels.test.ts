import { describe, expect, it } from 'vitest';

import {
  buildEditorTabLabels,
  editorDocumentResourcePath,
  editorTabLabelForDocument,
  editorTabLabelsForDocuments,
  formatAgentDraftTitle,
} from './editor-tab-labels';
import type { WorkspaceDocumentDescriptor } from './workspace-documents';

describe('editor-tab-labels', () => {
  it('uses basename when tab names are unique', () => {
    const labels = buildEditorTabLabels([
      { id: 'file:README.md', resourcePath: 'README.md' },
      { id: 'file:package.json', resourcePath: 'package.json' },
    ]);
    expect(labels.get('file:README.md')).toBe('README.md');
    expect(labels.get('file:package.json')).toBe('package.json');
  });

  it('disambiguates duplicate basenames with parent folders', () => {
    const labels = buildEditorTabLabels([
      { id: 'file:a', resourcePath: 'apps/console-web/README.md' },
      { id: 'file:b', resourcePath: 'services/control-plane/README.md' },
    ]);
    expect(labels.get('file:a')).toBe('console-web/README.md');
    expect(labels.get('file:b')).toBe('control-plane/README.md');
  });

  it('shows readable draft titles instead of slug ids', () => {
    const documents: WorkspaceDocumentDescriptor[] = [
      {
        id: 'file:README.md',
        title: 'README.md',
        language: 'markdown',
        value: '# Repo',
        description: 'file',
        source: 'file',
        filePath: 'README.md',
      },
      {
        id: 'draft:agent-search-returned-no-results-abc123',
        title: 'Agent · Cursor vs EduDash Pro: Images',
        language: 'markdown',
        value: '## Report',
        description: 'draft',
        source: 'draft',
      },
      {
        id: 'draft:agent-edit-review:apps-console-web-src-lib-foo.ts',
        title: 'foo.ts · review',
        language: 'plaintext',
        value: '# Agent review · apps/console-web/src/lib/foo.ts\n',
        description: 'review',
        source: 'draft',
        filePath: 'apps/console-web/src/lib/foo.ts',
      },
    ];

    const labels = editorTabLabelsForDocuments(documents);
    expect(labels.get('file:README.md')).toBe('README.md');
    expect(labels.get('draft:agent-search-returned-no-results-abc123')).toBe(
      'Cursor vs EduDash Pro: Imag…',
    );
    expect(labels.get('draft:agent-edit-review:apps-console-web-src-lib-foo.ts')).toBe(
      'foo.ts · review',
    );
    expect(editorDocumentResourcePath(documents[1])).toBe(
      'agent-reports/agent-search-returned-no-results-abc123.md',
    );
    expect(editorDocumentResourcePath(documents[2])).toBe('apps/console-web/src/lib/foo.ts');
    expect(editorTabLabelForDocument(documents[1], labels)).toBe('Cursor vs EduDash Pro: Imag…');
  });

  it('prefixes agent draft titles', () => {
    expect(formatAgentDraftTitle('Web search report')).toBe('Agent · Web search report');
    expect(formatAgentDraftTitle('Agent · Already prefixed')).toBe('Agent · Already prefixed');
  });
});
