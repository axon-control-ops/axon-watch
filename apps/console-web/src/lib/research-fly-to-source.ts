export type ResearchFlyToTarget = {
  path: string;
  line?: number;
  searchText?: string;
};

const WORKSPACE_FILE_WITH_LINE_RE =
  /(?:^|[\s('"`])([\w./-]+\.(?:ts|tsx|js|jsx|mjs|cjs|vue|py|md|json|css|html|sh|yaml|yml)):(\d{1,6})\b/i;

const WORKSPACE_FILE_RE =
  /(?:^|[\s('"`])([\w./-]+\.(?:ts|tsx|js|jsx|mjs|cjs|vue|py|md|json|css|html|sh|yaml|yml))\b/i;

const FILE_URL_RE = /^file:(?:\/\/\/|\/\/)(.+)$/i;

function normalizeWorkspacePath(raw: string): string {
  return raw.replace(/\\/g, '/').replace(/^\.\//, '').replace(/^\/+/, '').trim();
}

function extractFileFromText(text: string): ResearchFlyToTarget | null {
  const withLine = text.match(WORKSPACE_FILE_WITH_LINE_RE);
  if (withLine) {
    return {
      path: normalizeWorkspacePath(withLine[1]),
      line: Number(withLine[2]),
    };
  }

  const fileOnly = text.match(WORKSPACE_FILE_RE);
  if (fileOnly) {
    return { path: normalizeWorkspacePath(fileOnly[1]) };
  }

  return null;
}

function extractSearchTerm(query: string, snippet: string): string | undefined {
  const fromQuery = query
    .replace(/^(?:web\s+search|page\s+fetch|search|fetch)\s+/i, '')
    .trim();
  if (fromQuery.length >= 3 && fromQuery.length <= 80) {
    return fromQuery;
  }

  const firstLine = snippet
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.length >= 3);
  return firstLine?.slice(0, 80);
}

export function resolveResearchFlyToTarget(input: {
  title: string;
  url: string;
  snippet: string;
  query?: string;
}): ResearchFlyToTarget | null {
  const url = input.url.trim();
  if (url && url !== 'about:blank') {
    const fileUrl = url.match(FILE_URL_RE);
    if (fileUrl) {
      const path = normalizeWorkspacePath(decodeURIComponent(fileUrl[1]).split('#', 1)[0] ?? '');
      const hashLine = url.match(/#L(\d+)$/i);
      return {
        path,
        line: hashLine ? Number(hashLine[1]) : undefined,
      };
    }

    if (!/^https?:\/\//i.test(url)) {
      const pathMatch = url.match(WORKSPACE_FILE_WITH_LINE_RE) ?? url.match(WORKSPACE_FILE_RE);
      if (pathMatch) {
        return {
          path: normalizeWorkspacePath(pathMatch[1]),
          line: pathMatch[2] ? Number(pathMatch[2]) : undefined,
        };
      }
    }
  }

  for (const candidate of [input.snippet, input.title, input.query ?? '']) {
    const resolved = extractFileFromText(candidate);
    if (resolved) {
      if (!resolved.searchText && input.query) {
        resolved.searchText = extractSearchTerm(input.query, input.snippet);
      }
      return resolved;
    }
  }

  return null;
}

export function canFlyToWorkspaceSource(input: {
  title: string;
  url: string;
  snippet: string;
  query?: string;
}): boolean {
  return resolveResearchFlyToTarget(input) !== null;
}
