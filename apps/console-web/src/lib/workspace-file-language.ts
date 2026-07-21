const EXTENSION_LANGUAGE: Record<string, string> = {
  md: 'markdown',
  json: 'json',
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  py: 'python',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  txt: 'plaintext',
  // Vue SFCs: html highlighting only — do not map to typescript (ts.worker hang risk).
  vue: 'html',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'css',
  less: 'css',
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
const BINARY_EXTENSIONS = new Set([
  ...IMAGE_EXTENSIONS,
  'pdf',
  'zip',
  'gz',
  'tgz',
  'bz2',
  'xz',
  '7z',
  'rar',
  'exe',
  'dll',
  'so',
  'dylib',
  'bin',
  'wasm',
  'woff',
  'woff2',
  'ttf',
  'otf',
  'eot',
  'ico',
  'mp3',
  'mp4',
  'webm',
  'mov',
  'avi',
  'wav',
  'ogg',
  'sqlite',
  'sqlite3',
  'db',
  'apk',
  'aab',
  'dmg',
  'iso',
]);

export function languageForFilePath(path: string): string {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_LANGUAGE[extension] ?? 'plaintext';
}

export function isImageFilePath(path: string): boolean {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return IMAGE_EXTENSIONS.has(extension);
}

export function isBinaryFilePath(path: string): boolean {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return BINARY_EXTENSIONS.has(extension);
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
