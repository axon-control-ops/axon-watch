import { countAgentTranscriptHeaders } from './agent-transcript-blocks';
import type { AgentStreamCounts } from './agent-stream-incremental';

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

/**
 * Composer activity chips. Uses header counts only so streaming turns with
 * hundreds of edit bodies do not re-parse the full transcript every delta.
 */
export function summarizeIdeAgentActivityFromCounts(
  counts: AgentStreamCounts,
): IdeAgentActivitySummary {
  return buildIdeAgentActivitySummary(counts);
}

export function summarizeIdeAgentActivity(content: string): IdeAgentActivitySummary {
  return buildIdeAgentActivitySummary(countAgentTranscriptHeaders(content));
}

function buildIdeAgentActivitySummary(counts: AgentStreamCounts): IdeAgentActivitySummary {
  const chips: IdeAgentActivityChip[] = [];

  if (counts.research > 0) {
    chips.push({
      id: `search:${counts.research}`,
      kind: 'search',
      label: counts.research === 1 ? '1 search' : `${counts.research} searches`,
    });
  }
  if (counts.edit > 0) {
    chips.push({
      id: `file:${counts.edit}`,
      kind: 'file',
      label: counts.edit === 1 ? '1 file' : `${counts.edit} files`,
    });
  }
  if (counts.terminal > 0) {
    chips.push({
      id: `terminal:${counts.terminal}`,
      kind: 'terminal',
      label: counts.terminal === 1 ? '1 terminal' : `${counts.terminal} terminals`,
    });
  }
  if (counts.tool > 0) {
    chips.push({
      id: `tool:${counts.tool}`,
      kind: 'tool',
      label: counts.tool === 1 ? '1 tool call' : `${counts.tool} tool calls`,
    });
  }

  return {
    chips: chips.slice(-4),
    searchCount: counts.research,
    fileCount: counts.edit,
    terminalCount: counts.terminal,
    toolCount: counts.tool,
  };
}
