import { computed, type ComputedRef } from 'vue';

import {
  buildEditorAccessStatus,
  resolveEditorAccessReadOnlyReason,
  type EditorAccessStatus,
} from '../lib/editor-access-status-view';
import { buildEditorLanguageLabel } from '../lib/editor-language-label';
import type { WorkspaceDocumentDescriptor } from '../lib/workspace-documents';

type ActiveEditorDocument = WorkspaceDocumentDescriptor | null | undefined;

export function useEditorStatusBarMeta(input: {
  activeDocument: ComputedRef<ActiveEditorDocument>;
  activeEditorValue: ComputedRef<string>;
  isAgentEditReviewDocument: ComputedRef<boolean>;
  isMarkdownEditorDocument: ComputedRef<boolean>;
  isBinaryEditorDocument: ComputedRef<boolean>;
  isImageEditorDocument: ComputedRef<boolean>;
}): {
  editorLineCount: ComputedRef<number>;
  editorEol: ComputedRef<'CRLF' | 'LF'>;
  editorLanguageLabel: ComputedRef<string>;
  editorAccessStatus: ComputedRef<EditorAccessStatus>;
} {
  const editorLineCount = computed(() => {
    const value = input.activeEditorValue.value;
    return value.length === 0 ? 1 : value.split(/\r\n|\r|\n/).length;
  });

  const editorEol = computed((): 'CRLF' | 'LF' =>
    input.activeEditorValue.value.includes('\r\n') ? 'CRLF' : 'LF',
  );

  const editorLanguageLabel = computed(() => {
    const document = input.activeDocument.value;
    return buildEditorLanguageLabel({
      language: document?.language ?? 'plaintext',
      filePath:
        document?.source === 'file' ? (document.filePath ?? document.title) : null,
      isAgentEditReview: input.isAgentEditReviewDocument.value,
      isMarkdownEditorDocument: input.isMarkdownEditorDocument.value,
    });
  });

  const editorAccessStatus = computed(() => {
    const document = input.activeDocument.value;
    const readOnlyReason = resolveEditorAccessReadOnlyReason({
      readOnly: document?.readOnly ?? false,
      source: document?.source,
      planId: document?.planId,
      description: document?.description,
      isAgentEditReview: input.isAgentEditReviewDocument.value,
      isMarkdownEditorDocument: input.isMarkdownEditorDocument.value,
      isBinaryEditorDocument: input.isBinaryEditorDocument.value,
      isImageEditorDocument: input.isImageEditorDocument.value,
    });
    return buildEditorAccessStatus({
      hasDocument: Boolean(document),
      readOnly: document?.readOnly ?? false,
      dirty: document?.dirty ?? false,
      readOnlyReason,
    });
  });

  return {
    editorLineCount,
    editorEol,
    editorLanguageLabel,
    editorAccessStatus,
  };
}
