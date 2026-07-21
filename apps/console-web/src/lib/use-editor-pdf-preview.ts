import { computed, type ComputedRef } from 'vue';

import { resolveWorkspaceFileRawUrl } from '../api/workspace-api';
import { isPdfFilePath } from './workspace-file-language';

type EditorDocumentLike = {
  source: string;
  filePath?: string | null;
  title: string;
} | null | undefined;

type WorkspaceLike = {
  workspace_id?: string | null;
} | null | undefined;

export function useEditorPdfPreview(options: {
  activeDocument: ComputedRef<EditorDocumentLike> | { value: EditorDocumentLike };
  workspace: ComputedRef<WorkspaceLike> | { value: WorkspaceLike };
}) {
  const isPdfEditorDocument = computed(() => {
    const document = options.activeDocument.value;
    if (!document || document.source !== 'file') {
      return false;
    }
    return isPdfFilePath(document.filePath ?? document.title);
  });

  const editorPdfPreviewUrl = computed(() => {
    const document = options.activeDocument.value;
    const workspaceId = options.workspace.value?.workspace_id;
    if (!document || !workspaceId || !isPdfEditorDocument.value || document.source !== 'file') {
      return '';
    }
    const filePath = document.filePath ?? document.title;
    return resolveWorkspaceFileRawUrl(workspaceId, filePath);
  });

  return { isPdfEditorDocument, editorPdfPreviewUrl };
}
