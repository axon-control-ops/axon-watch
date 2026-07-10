import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

export type IdeAgentActivityChip = {
  id: string;
  kind: 'search' | 'file' | 'terminal' | 'tool';
  label: string;
};

export type IdeAgentActivitySummary = {
  chips: IdeAgentActivityChip[];
  searchCount: number;
  fileCount: number;
  terminalCount: number;
  toolCount: number;
};

export function summarizeIdeAgentActivity(content: string): IdeAgentActivitySummary {
  const chips: IdeAgentActivityChip[] = [];
  let searchCount = 0;
  let fileCount = 0;
  let terminalCount = 0;
  let toolCount = 0;

  for (const segment of parseAgentTranscriptBlocks(content)) {
    if (segment.kind === 'research') {
      searchCount += 1;
      chips.push({
        id: `search:${searchCount}:${segment.query}`,
        kind: 'search',
        label: searchCount === 1 ? '1 search' : `${searchCount} searches`,
      });
      continue;
    }
    if (segment.kind === 'edit') {
      fileCount += 1;
      chips.push({
        id: `file:${fileCount}:${segment.path}`,
        kind: 'file',
        label: fileCount === 1 ? '1 file' : `${fileCount} files`,
      });
      continue;
    }
    if (segment.kind === 'terminal') {
      terminalCount += 1;
      chips.push({
        id: `terminal:${terminalCount}:${segment.command}`,
        kind: 'terminal',
        label: terminalCount === 1 ? '1 terminal' : `${terminalCount} terminals`,
      });
      continue;
    }
    if (segment.kind === 'tool') {
      toolCount += 1;
    }
  }

  if (toolCount > 0) {
    chips.push({
      id: `tool:${toolCount}`,
      kind: 'tool',
      label: toolCount === 1 ? '1 tool call' : `${toolCount} tool calls`,
    });
  }

  const deduped: IdeAgentActivityChip[] = [];
  for (const chip of chips) {
    const previous = deduped[deduped.length - 1];
    if (previous?.kind === chip.kind && previous.label === chip.label) {
      continue;
    }
    deduped.push(chip);
  }

  return {
    chips: deduped.slice(-4),
    searchCount,
    fileCount,
    terminalCount,
    toolCount,
  };
}
