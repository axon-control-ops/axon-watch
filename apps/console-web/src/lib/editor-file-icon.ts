export type EditorFileIconTone =
  | 'default'
  | 'markdown'
  | 'json'
  | 'typescript'
  | 'javascript'
  | 'python'
  | 'shell'
  | 'html'
  | 'css'
  | 'csv'
  | 'yaml'
  | 'sql'
  | 'image'
  | 'config';

const EXTENSION_ICON_TONE: Record<string, EditorFileIconTone> = {
  md: 'markdown',
  mdx: 'markdown',
  json: 'json',
  jsonc: 'json',
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
  csv: 'csv',
  tsv: 'csv',
  yaml: 'yaml',
  yml: 'yaml',
  xml: 'html',
  html: 'html',
  htm: 'html',
  vue: 'html',
  css: 'css',
  scss: 'css',
  less: 'css',
  sql: 'sql',
  toml: 'config',
  ini: 'config',
  env: 'config',
  rs: 'typescript',
  go: 'typescript',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  webp: 'image',
  bmp: 'image',
  svg: 'image',
  avif: 'image',
};

export function editorFileIconToneForPath(path: string): EditorFileIconTone {
  const extension = path.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_ICON_TONE[extension] ?? 'default';
}

export function editorFileIconToneForDocument(input: {
  title: string;
  filePath?: string | null;
  language?: string | null;
}): EditorFileIconTone {
  const path = input.filePath ?? input.title;
  const fromPath = editorFileIconToneForPath(path);
  if (fromPath !== 'default') {
    return fromPath;
  }

  switch (input.language) {
    case 'markdown':
      return 'markdown';
    case 'json':
      return 'json';
    case 'typescript':
      return 'typescript';
    case 'javascript':
      return 'javascript';
    case 'python':
      return 'python';
    case 'shell':
      return 'shell';
    case 'html':
      return 'html';
    case 'css':
      return 'css';
    case 'csv':
      return 'csv';
    case 'image':
      return 'image';
    default:
      return 'default';
  }
}

export function editorFileIconLabelForTone(tone: EditorFileIconTone): string {
  switch (tone) {
    case 'markdown':
      return 'MD';
    case 'json':
      return '{}';
    case 'typescript':
      return 'TS';
    case 'javascript':
      return 'JS';
    case 'python':
      return 'PY';
    case 'shell':
      return 'SH';
    case 'html':
      return '<>';
    case 'css':
      return '#';
    case 'csv':
      return 'CSV';
    case 'yaml':
      return 'YML';
    case 'sql':
      return 'SQL';
    case 'image':
      return 'IMG';
    case 'config':
      return 'CFG';
    default:
      return 'FILE';
  }
}
