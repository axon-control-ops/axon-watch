import { isSafeWorkspaceFilePath, normalizeWorkspaceFilePath } from './workspace-file-session';

export type MarkdownLinkTarget =
  | { kind: 'workspace'; path: string }
  | { kind: 'external'; url: string }
  | { kind: 'anchor'; hash: string }
  | { kind: 'skip' };

const EXTERNAL_LINK_PATTERN = /^(?:https?:|mailto:|tel:)/i;

export function resolveRelativeWorkspacePath(baseFilePath: string, relativeHref: string): string {
  const normalizedBase = normalizeWorkspaceFilePath(baseFilePath.replace(/\\/g, '/'));
  const baseDir = normalizedBase.includes('/')
    ? normalizedBase.slice(0, normalizedBase.lastIndexOf('/'))
    : '';
  const segments = [
    ...(baseDir ? baseDir.split('/') : []),
    ...relativeHref.replace(/\\/g, '/').split('/'),
  ];
  const resolved: string[] = [];
  for (const segment of segments) {
    if (!segment || segment === '.') {
      continue;
    }
    if (segment === '..') {
      resolved.pop();
      continue;
    }
    resolved.push(segment);
  }
  return resolved.join('/');
}

export function resolveMarkdownLinkTarget(
  href: string,
  baseFilePath?: string | null,
): MarkdownLinkTarget {
  const trimmed = href.trim();
  if (!trimmed || trimmed === '#') {
    return { kind: 'skip' };
  }
  if (trimmed.startsWith('#')) {
    return { kind: 'anchor', hash: trimmed };
  }
  if (EXTERNAL_LINK_PATTERN.test(trimmed)) {
    return { kind: 'external', url: trimmed };
  }

  let path = trimmed.replace(/\\/g, '/');
  if (path.startsWith('/')) {
    path = normalizeWorkspaceFilePath(path);
  } else if (
    baseFilePath &&
    (path.startsWith('./') || path.startsWith('../') || !path.includes('/'))
  ) {
    path = resolveRelativeWorkspacePath(baseFilePath, path);
  } else {
    path = normalizeWorkspaceFilePath(path);
  }

  if (!isSafeWorkspaceFilePath(path)) {
    return { kind: 'skip' };
  }

  return { kind: 'workspace', path };
}

function defaultOpenExternal(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}

export function handleMarkdownContainerClick(
  event: MouseEvent,
  options: {
    openWorkspaceFile: (path: string) => void | Promise<void>;
    openExternalUrl?: (url: string) => void;
    baseFilePath?: string | null;
  },
): void {
  const anchor = (event.target as HTMLElement | null)?.closest('a');
  if (!anchor) {
    return;
  }

  const href = anchor.getAttribute('href');
  if (!href) {
    return;
  }

  const target = resolveMarkdownLinkTarget(href, options.baseFilePath);
  if (target.kind === 'skip') {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  switch (target.kind) {
    case 'workspace':
      void options.openWorkspaceFile(target.path);
      return;
    case 'external':
      (options.openExternalUrl ?? defaultOpenExternal)(target.url);
      return;
    case 'anchor': {
      const id = target.hash.slice(1);
      if (!id) {
        return;
      }
      const root = anchor.closest('.conversation-seam__content--markdown');
      const heading = root?.querySelector(`[id="${CSS.escape(id)}"]`);
      heading?.scrollIntoView({ block: 'nearest' });
      return;
    }
    default:
      return;
  }
}
