import { computed } from 'vue';
import { describe, expect, it } from 'vitest';

import type { WorkspaceDocumentDescriptor } from '../lib/workspace-documents';
import { useEditorStatusBarMeta } from './useEditorStatusBarMeta';

function document(
  overrides: Partial<WorkspaceDocumentDescriptor> = {},
): WorkspaceDocumentDescriptor {
  return {
    id: 'file:README.md',
    title: 'README.md',
    language: 'markdown',
    value: '# Hello',
    description: '',
    source: 'file',
    filePath: 'README.md',
    readOnly: false,
    dirty: false,
    ...overrides,
  };
}

describe('useEditorStatusBarMeta', () => {
  it('derives line count, EOL, language label, and unsaved access status', () => {
    const activeDocument = computed(() =>
      document({ dirty: true, value: 'line one\r\nline two' }),
    );
    const { editorLineCount, editorEol, editorLanguageLabel, editorAccessStatus } =
      useEditorStatusBarMeta({
        activeDocument,
        activeEditorValue: computed(() => activeDocument.value?.value ?? ''),
        isAgentEditReviewDocument: computed(() => false),
        isMarkdownEditorDocument: computed(() => true),
        isBinaryEditorDocument: computed(() => false),
        isImageEditorDocument: computed(() => false),
      });

    expect(editorLineCount.value).toBe(2);
    expect(editorEol.value).toBe('CRLF');
    expect(editorLanguageLabel.value).toBe('Markdown');
    expect(editorAccessStatus.value).toMatchObject({
      label: 'Unsaved',
      tone: 'unsaved',
      opensSourceControl: true,
    });
  });

  it('maps read-only image previews to preview access status', () => {
    const activeDocument = computed(() =>
      document({
        language: 'image',
        readOnly: true,
        value: '',
      }),
    );
    const { editorAccessStatus } = useEditorStatusBarMeta({
      activeDocument,
      activeEditorValue: computed(() => ''),
      isAgentEditReviewDocument: computed(() => false),
      isMarkdownEditorDocument: computed(() => false),
      isBinaryEditorDocument: computed(() => false),
      isImageEditorDocument: computed(() => true),
    });

    expect(editorAccessStatus.value).toMatchObject({
      label: 'Preview',
      tone: 'preview',
      opensSourceControl: false,
    });
  });
});
