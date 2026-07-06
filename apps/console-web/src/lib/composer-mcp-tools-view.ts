export type ComposerMcpTool = {
  id: string;
  label: string;
  bounded_context: string;
  mode_support: string[];
};

export type ComposerMcpToolsSnapshot = {
  count: number;
  items: ComposerMcpTool[];
};

export type IdeComposerMode = 'ask' | 'plan' | 'agent';

export function filterMcpToolsForComposerMode(
  snapshot: ComposerMcpToolsSnapshot | null,
  mode: IdeComposerMode,
): ComposerMcpTool[] {
  if (!snapshot?.items?.length) {
    return [];
  }
  return snapshot.items.filter((item) =>
    item.mode_support.map((entry) => entry.toLowerCase()).includes(mode),
  );
}

export function mcpToolDetail(tool: ComposerMcpTool): string {
  return `${tool.bounded_context} · ${tool.id}`;
}
