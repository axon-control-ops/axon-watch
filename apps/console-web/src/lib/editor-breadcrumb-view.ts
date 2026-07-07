export type EditorBreadcrumbSegmentKind = 'workspace' | 'folder' | 'file' | 'symbol';

export type EditorBreadcrumbSegment = {
  id: string;
  label: string;
  kind: EditorBreadcrumbSegmentKind;
  revealLine?: number;
};

export type MarkdownHeadingSymbol = {
  line: number;
  level: number;
  text: string;
};

const HEADING_PATTERN = /^(#{1,6})\s+(.+?)\s*$/;

/** Markdown headings for symbol breadcrumbs (VS Code / Cursor-style). */
export function parseMarkdownHeadingSymbols(content: string): MarkdownHeadingSymbol[] {
  const symbols: MarkdownHeadingSymbol[] = [];
  const lines = content.split(/\r\n|\r|\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const match = HEADING_PATTERN.exec(lines[index] ?? '');
    if (!match) {
      continue;
    }
    symbols.push({
      line: index + 1,
      level: match[1].length,
      text: match[2].trim(),
    });
  }

  return symbols;
}

/** Active markdown heading at or above the cursor line. */
export function resolveMarkdownSymbolAtLine(
  content: string,
  line: number,
): MarkdownHeadingSymbol | null {
  if (line < 1) {
    return null;
  }

  let active: MarkdownHeadingSymbol | null = null;
  for (const symbol of parseMarkdownHeadingSymbols(content)) {
    if (symbol.line > line) {
      break;
    }
    active = symbol;
  }
  return active;
}

function pathSegments(path: string): string[] {
  return path
    .replace(/\\/g, '/')
    .split('/')
    .map((segment) => segment.trim())
    .filter(Boolean);
}

/** Workspace-relative file path split into breadcrumb segments. */
export function buildEditorPathSegments(
  workspaceId: string,
  filePath: string,
): EditorBreadcrumbSegment[] {
  const segments = pathSegments(filePath);
  const trail: EditorBreadcrumbSegment[] = [
    {
      id: `workspace:${workspaceId}`,
      label: workspaceId,
      kind: 'workspace',
    },
  ];

  if (segments.length === 0) {
    return trail;
  }

  for (let index = 0; index < segments.length - 1; index += 1) {
    const label = segments[index];
    trail.push({
      id: `folder:${segments.slice(0, index + 1).join('/')}`,
      label,
      kind: 'folder',
    });
  }

  const fileName = segments[segments.length - 1];
  trail.push({
    id: `file:${filePath}`,
    label: fileName,
    kind: 'file',
  });

  return trail;
}

export function buildEditorBreadcrumbTrail(options: {
  workspaceId: string;
  filePath: string;
  content: string;
  cursorLine: number;
  language: string;
}): EditorBreadcrumbSegment[] {
  const pathTrail = buildEditorPathSegments(options.workspaceId, options.filePath);
  if (options.language !== 'markdown') {
    return pathTrail;
  }

  const symbol = resolveMarkdownSymbolAtLine(options.content, options.cursorLine);
  if (!symbol) {
    return pathTrail;
  }

  return [
    ...pathTrail,
    {
      id: `symbol:${symbol.line}:${symbol.text}`,
      label: symbol.text,
      kind: 'symbol',
      revealLine: symbol.line,
    },
  ];
}
