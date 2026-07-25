export const EDITOR_MARKDOWN_PREVIEW_KEY = 'axon-x-editor-markdown-preview-v1';

type EditorPreviewMap = Record<string, boolean>;

function readPreviewMap(): EditorPreviewMap {
  if (typeof window === 'undefined') {
    return {};
  }

  const raw = window.localStorage.getItem(EDITOR_MARKDOWN_PREVIEW_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }

    const map: EditorPreviewMap = {};
    for (const [documentId, enabled] of Object.entries(parsed)) {
      if (typeof enabled === 'boolean') {
        map[documentId] = enabled;
      }
    }
    return map;
  } catch {
    return {};
  }
}

function writePreviewMap(map: EditorPreviewMap): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(EDITOR_MARKDOWN_PREVIEW_KEY, JSON.stringify(map));
}

export function readEditorMarkdownPreviewEnabled(documentId: string): boolean | null {
  return readPreviewMap()[documentId] ?? null;
}

export function persistEditorMarkdownPreviewEnabled(
  documentId: string,
  enabled: boolean,
): void {
  const map = readPreviewMap();
  map[documentId] = enabled;
  writePreviewMap(map);
}

export function resolveEditorMarkdownPreviewEnabled(
  documentId: string,
  isMarkdownDocument: boolean,
  preferPreview = false,
): boolean {
  if (!isMarkdownDocument) {
    return false;
  }

  const stored = readEditorMarkdownPreviewEnabled(documentId);
  if (stored !== null) {
    return stored;
  }

  return preferPreview;
}
