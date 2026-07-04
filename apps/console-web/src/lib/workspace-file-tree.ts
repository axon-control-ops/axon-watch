export interface WorkspaceFileTreeNode {
  name: string;
  path: string;
  kind: 'file' | 'directory';
  children?: WorkspaceFileTreeNode[];
}

export function buildWorkspaceFileTree(
  entries: Array<{ path: string; size_bytes: number }>,
): WorkspaceFileTreeNode[] {
  const root: WorkspaceFileTreeNode[] = [];
  const directoryNodes = new Map<string, WorkspaceFileTreeNode>();

  for (const entry of [...entries].sort((left, right) => left.path.localeCompare(right.path))) {
    const parts = entry.path.split('/');
    let currentLevel = root;
    let currentPath = '';

    for (let index = 0; index < parts.length; index += 1) {
      const part = parts[index] ?? '';
      const isFile = index === parts.length - 1;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (isFile) {
        currentLevel.push({
          name: part,
          path: entry.path,
          kind: 'file',
        });
        continue;
      }

      let directoryNode = directoryNodes.get(currentPath);
      if (!directoryNode) {
        directoryNode = {
          name: part,
          path: currentPath,
          kind: 'directory',
          children: [],
        };
        directoryNodes.set(currentPath, directoryNode);
        currentLevel.push(directoryNode);
      }

      currentLevel = directoryNode.children ?? [];
    }
  }

  return root;
}

export interface WorkspaceFileTreeRow {
  path: string;
  name: string;
  kind: 'file' | 'directory';
  depth: number;
}

export function flattenWorkspaceFileTree(
  nodes: WorkspaceFileTreeNode[],
  expandedDirectories: Record<string, boolean>,
  depth = 0,
): WorkspaceFileTreeRow[] {
  const rows: WorkspaceFileTreeRow[] = [];

  for (const node of nodes) {
    rows.push({
      path: node.path,
      name: node.name,
      kind: node.kind,
      depth,
    });

    if (
      node.kind === 'directory' &&
      (expandedDirectories[node.path] ?? true) &&
      node.children?.length
    ) {
      rows.push(...flattenWorkspaceFileTree(node.children, expandedDirectories, depth + 1));
    }
  }

  return rows;
}
