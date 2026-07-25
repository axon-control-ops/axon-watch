import { isSafeWorkspaceFilePath, normalizeWorkspaceFilePath } from './workspace-file-session';

/** Extensions we turn into clickable workspace file links in agent prose. */
const LINKABLE_EXTENSIONS = [
  'md',
  'markdown',
  'json',
  'ts',
  'tsx',
  'js',
  'jsx',
  'mjs',
  'cjs',
  'py',
  'sh',
  'bash',
  'zsh',
  'txt',
  'vue',
  'html',
  'htm',
  'css',
  'scss',
  'less',
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
  'bmp',
  'svg',
  'avif',
  'pdf',
  'toml',
  'yaml',
  'yml',
  'rs',
  'go',
  'java',
  'kt',
  'swift',
  'rb',
  'php',
  'sql',
  'csv',
  'xml',
  'lock',
  'ini',
  'cfg',
  'conf',
] as const;

const EXT_ALT = LINKABLE_EXTENSIONS.join('|');

/** Relative workspace path with at least one directory segment. */
const RELATIVE_PATH_RE = new RegExp(
  String.raw`(?<![\w./-])(\`?)([A-Za-z0-9_.@+-]+(?:/[A-Za-z0-9_.@+-]+)+\.(?:${EXT_ALT}))\1(?![\w./-])`,
  'gi',
);

/** Bare filename with a linkable extension (used inside Files (in …) lists). */
const BARE_FILENAME_RE = new RegExp(
  String.raw`^(?:\`?)([A-Za-z0-9_.@+-]+\.(?:${EXT_ALT}))(?:\`?)$`,
  'i',
);

const FILES_IN_DIR_RE =
  /(?:^|\n)([ \t]*)(?:\*\*)?Files?\s*\(\s*in\s+[`"'“]?([^)`"'”\n]+)[`"'”]?\s*\)\s*:?(?:\*\*)?[ \t]*(?:\n[ \t]*)*\n((?:[ \t]*[-*+][ \t]+.+\n?)+)/gi;

const FENCE_SPLIT_RE = /(```[\s\S]*?```|~~~[\s\S]*?~~~)/g;
const MD_LINK_OR_IMAGE_RE = /(!?\[[^\]]*]\([^)]+\))/g;

function toMarkdownFileLink(label: string, path: string): string {
  const normalized = normalizeWorkspaceFilePath(path);
  if (!normalized || !isSafeWorkspaceFilePath(normalized)) {
    return label;
  }
  // Escape unbalanced brackets/parens lightly for markdown link safety.
  const safeLabel = label.replace(/[\[\]]/g, '');
  const safeHref = normalized.replace(/[()\s]/g, (ch) => encodeURIComponent(ch));
  return `[${safeLabel}](${safeHref})`;
}

/**
 * Expand "Files (in output/signs/):" bullet lists so bare filenames become
 * full workspace paths that can open in the editor/canvas.
 */
export function expandAgentFileDirectoryLists(markdown: string): string {
  return String(markdown || '').replace(FILES_IN_DIR_RE, (full, indent, rawDir, listBlock) => {
    const directory = normalizeWorkspaceFilePath(String(rawDir || '').replace(/\/+$/, ''));
    if (!directory || !isSafeWorkspaceFilePath(directory)) {
      return full;
    }

    const rewritten = String(listBlock)
      .split('\n')
      .map((line) => {
        const match = line.match(/^([ \t]*[-*+][ \t]+)(.+?)([ \t]*)$/);
        if (!match) {
          return line;
        }
        const [, bullet, item] = match;
        const bare = String(item || '').trim().match(BARE_FILENAME_RE);
        if (!bare?.[1]) {
          return line;
        }
        const fileName = bare[1];
        if (fileName.includes('/')) {
          return line;
        }
        const fullPath = `${directory}/${fileName}`;
        return `${bullet}${toMarkdownFileLink(fileName, fullPath)}`;
      })
      .join('\n');

    const prefix = full.startsWith('\n') ? '\n' : '';
    return `${prefix}${indent}Files (in ${directory}/):\n${rewritten}`;
  });
}

function linkifyOutsideMarkdownLinks(chunk: string): string {
  const parts = chunk.split(MD_LINK_OR_IMAGE_RE);
  return parts
    .map((part, index) => {
      // Odd indices are existing markdown links/images — leave untouched.
      if (index % 2 === 1 || !part) {
        return part;
      }
      return part.replace(RELATIVE_PATH_RE, (_full, _tick, path: string) =>
        toMarkdownFileLink(path, path),
      );
    })
    .join('');
}

/**
 * Turn bare workspace-relative paths in agent markdown into clickable links.
 * Skips fenced code blocks and existing markdown links.
 */
export function linkifyWorkspacePathsInMarkdown(markdown: string): string {
  const source = expandAgentFileDirectoryLists(markdown);
  const segments = source.split(FENCE_SPLIT_RE);
  return segments
    .map((segment, index) => {
      if (index % 2 === 1) {
        return segment;
      }
      return linkifyOutsideMarkdownLinks(segment);
    })
    .join('');
}
