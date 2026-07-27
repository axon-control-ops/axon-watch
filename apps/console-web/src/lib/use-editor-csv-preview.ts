import { computed, ref, watch, type ComputedRef } from 'vue';

import { csvTablePreviewFromRaw } from './editor-csv-table-view';
import { isTabularFilePath } from './workspace-file-language';

type EditorDocumentLike = {
  id: string;
  source: string;
  language?: string | null;
  filePath?: string | null;
  title: string;
  value?: string;
} | null | undefined;

export function useEditorCsvPreview(options: {
  activeDocument: ComputedRef<EditorDocumentLike> | { value: EditorDocumentLike };
  activeEditorValue: ComputedRef<string> | { value: string };
}) {
  const csvTablePreviewEnabled = ref(true);

  const isCsvEditorDocument = computed(() => {
    const document = options.activeDocument.value;
    if (!document) {
      return false;
    }
    if (document.language === 'csv') {
      return true;
    }
    const path = document.filePath ?? document.title;
    return document.source === 'file' && isTabularFilePath(path);
  });

  watch(
    () => options.activeDocument.value?.id,
    (documentId) => {
      if (!documentId) {
        csvTablePreviewEnabled.value = true;
        return;
      }
      csvTablePreviewEnabled.value = true;
    },
    { immediate: true },
  );

  const editorCsvTableHtml = computed(() => {
    if (!isCsvEditorDocument.value) {
      return '';
    }
    const document = options.activeDocument.value;
    const path =
      document?.source === 'file'
        ? document.filePath ?? document.title
        : document?.title ?? null;
    return csvTablePreviewFromRaw(options.activeEditorValue.value, path);
  });

  function setCsvTablePreviewMode(enabled: boolean): void {
    if (!isCsvEditorDocument.value) {
      return;
    }
    csvTablePreviewEnabled.value = enabled;
  }

  return {
    isCsvEditorDocument,
    csvTablePreviewEnabled,
    editorCsvTableHtml,
    setCsvTablePreviewMode,
  };
}
