import { describe, expect, it } from 'vitest';

import {
  filterMcpToolsForComposerMode,
  mcpToolDetail,
  type ComposerMcpToolsSnapshot,
} from './composer-mcp-tools-view';

const SNAPSHOT: ComposerMcpToolsSnapshot = {
  count: 3,
  items: [
    {
      id: 'workspace_files.read',
      label: 'Read workspace file',
      bounded_context: 'workspace_files',
      mode_support: ['ask', 'plan', 'agent', 'debug'],
    },
    {
      id: 'runs.history',
      label: 'Read persisted run history',
      bounded_context: 'runs',
      mode_support: ['plan', 'agent', 'debug'],
    },
    {
      id: 'vault.status',
      label: 'Inspect vault posture',
      bounded_context: 'vault',
      mode_support: ['ask', 'agent'],
    },
  ],
};

describe('filterMcpToolsForComposerMode', () => {
  it('returns only tools supported by the active composer mode', () => {
    expect(filterMcpToolsForComposerMode(SNAPSHOT, 'ask').map((tool) => tool.id)).toEqual([
      'workspace_files.read',
      'vault.status',
    ]);
    expect(filterMcpToolsForComposerMode(SNAPSHOT, 'plan').map((tool) => tool.id)).toEqual([
      'workspace_files.read',
      'runs.history',
    ]);
    expect(filterMcpToolsForComposerMode(SNAPSHOT, 'debug').map((tool) => tool.id)).toEqual([
      'workspace_files.read',
      'runs.history',
    ]);
  });
});

describe('mcpToolDetail', () => {
  it('formats bounded context and id', () => {
    expect(mcpToolDetail(SNAPSHOT.items[0])).toBe('workspace_files · workspace_files.read');
  });
});
