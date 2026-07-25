import { computed, type ComputedRef } from 'vue';

import { editorDocumentResourcePath } from './editor-tab-labels';
import {
  buildEditorBreadcrumbTrail,
  resolveEditorBreadcrumbFilePath,
  type EditorBreadcrumbSegment,
} from './editor-breadcrumb-view';
import type { WorkspaceDocumentDescriptor } from './workspace-documents';

export function useEditorBreadcrumbSegments(options: {
  activeDocument: ComputedRef<WorkspaceDocumentDescriptor | null | undefined> | {
    value: WorkspaceDocumentDescriptor | null | undefined;
  };
  activeEditorValue: ComputedRef<string> | { value: string };
  workspaceId: ComputedRef<string | null | undefined> | { value: string | null | undefined };
  cursorLine: ComputedRef<number> | { value: number };
}): ComputedRef<EditorBreadcrumbSegment[]> {
  return computed((): EditorBreadcrumbSegment[] => {
    const workspace = options.workspaceId.value ?? 'workspace_smoke';
    const document = options.activeDocument.value;
    if (!document) {
      return buildEditorBreadcrumbTrail({
        workspaceId: workspace,
        filePath: 'README.md',
        content: '',
        cursorLine: options.cursorLine.value,
        language: 'markdown',
      });
    }

    const filePath = resolveEditorBreadcrumbFilePath({
      source: document.source,
      filePath: document.filePath,
      id: document.id,
      title: document.title,
      value: options.activeEditorValue.value,
      resourcePath: editorDocumentResourcePath(document),
    });

    return buildEditorBreadcrumbTrail({
      workspaceId: workspace,
      filePath,
      content: options.activeEditorValue.value,
      cursorLine: options.cursorLine.value,
      language: document.language,
    });
  });
}
