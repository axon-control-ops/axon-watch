const EXTENSION_LANGUAGE: Record<string, string> = {
  md: 'markdown',
  json: 'json',
  ts: 'typescript',
  js: 'javascript',
  py: 'python',
  sh: 'shell',
  txt: 'plaintext',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  webp: 'image',
  bmp: 'image',
  svg: 'image',
  avif: 'image',
};

const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'avif']);

export function languageForFilePath(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_LANGUAGE[extension] ?? 'plaintext';
}

export function isImageFilePath(path: string): boolean {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return IMAGE_EXTENSIONS.has(extension);
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
