export function titleFromWorkspaceId(value: string): string {
  const withoutPrefix = value.trim().replace(/^workspace[_-]?/i, '');
  return withoutPrefix
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .split(/[_\-\s.]+/)
    .filter(Boolean)
    .map((part) => {
      if (part.toUpperCase() === part && part.length <= 4) {
        return part;
      }
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(' ');
}

export function workspaceIdFromLabel(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return '';
  }
  if (/^workspace[_-]/i.test(trimmed)) {
    return trimmed
      .replace(/\s+/g, '_')
      .replace(/[^a-zA-Z0-9_.-]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '');
  }
  const slug = trimmed
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');
  return slug ? `workspace_${slug}` : '';
}
