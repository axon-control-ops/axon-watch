const EXTENSION_LANGUAGE: Record<string, string> = {
  md: 'markdown',
  json: 'json',
  ts: 'typescript',
  js: 'javascript',
  py: 'python',
  sh: 'shell',
  txt: 'plaintext',
};

export function languageForFilePath(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_LANGUAGE[extension] ?? 'plaintext';
}

export function workspaceFileDocumentId(path: string): string {
  return `file:${path}`;
}

export function isFileDocumentId(id: string): boolean {
  return id.startsWith('file:');
}

export function filePathFromDocumentId(id: string): string | null {
  return isFileDocumentId(id) ? id.slice('file:'.length) : null;
}
