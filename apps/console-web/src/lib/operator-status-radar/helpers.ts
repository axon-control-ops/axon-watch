import type { OperatorBriefing } from '../../contracts/canonical';
import {
  agentContentHasTranscriptBlocks,
  parseAgentTranscriptBlocks,
} from '../agent-transcript-blocks';

export function truncatePanelCopy(value: string, maxLength = 96): string {
  const trimmed = value.trim().replace(/\s+/g, ' ');
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 1).trimEnd()}…`;
}

export function elapsedLabel(startedAt: string | null, endedAt: string | null, updatedAt: string | null): string {
  if (!startedAt) {
    return '—';
  }

  const startMs = Date.parse(startedAt);
  const endMs = Date.parse(endedAt ?? updatedAt ?? startedAt);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs < startMs) {
    return '—';
  }

  const totalSeconds = Math.max(0, Math.round((endMs - startMs) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const remMinutes = minutes % 60;
    if (hours >= 48) {
      const days = Math.floor(hours / 24);
      const remHours = hours % 24;
      return `${days}d ${remHours}h`;
    }
    return `${hours}h ${String(remMinutes).padStart(2, '0')}m`;
  }

  if (minutes > 0) {
    return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  }
  return `${seconds}s`;
}

export function firstMeaningfulLine(content: string | null | undefined): string {
  if (!content) {
    return 'No agent output yet';
  }

  const trimmed = content.trim();
  if (agentContentHasTranscriptBlocks(trimmed)) {
    const segments = parseAgentTranscriptBlocks(trimmed);
    for (let index = segments.length - 1; index >= 0; index -= 1) {
      const segment = segments[index];
      if (segment.kind === 'text' && segment.text.trim()) {
        const line = segment.text
          .split('\n')
          .map((entry) => entry.trim())
          .find((entry) => entry.length > 0);
        if (line) {
          return truncatePanelCopy(line);
        }
      }
      if (segment.kind === 'edit') {
        return truncatePanelCopy(`Edited ${segment.path}`);
      }
    }
  }

  const lines = trimmed
    .split('\n')
    .map((line) => line.trim())
    .filter(
      (line) =>
        line.length > 0 &&
        line !== '```' &&
        !line.startsWith(':::') &&
        line !== ':::',
    );

  return truncatePanelCopy(lines[0] ?? 'No agent output yet');
}

export function countHighPrioritySignals(briefing: OperatorBriefing | null): number {
  return (
    briefing?.top_signals.filter(
      (signal) => signal.severity === 'high' || signal.severity === 'critical',
    ).length ?? 0
  );
}
