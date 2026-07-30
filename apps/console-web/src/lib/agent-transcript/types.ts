import type { ResearchBlockKind } from '../research-provider';

export type ResearchTranscriptItem = {
  title: string;
  url: string;
  snippet: string;
};
export type AgentTranscriptSegment =
  | { kind: 'text'; text: string }
  | { kind: 'thinking'; text: string; open: boolean }
  | {
      kind: 'edit';
      path: string;
      added: number;
      removed: number;
      diff: string;
      open: boolean;
    }
  | { kind: 'tool'; label: string }
  | { kind: 'plan'; planId: string; title: string }
  | {
      kind: 'question';
      prompt: string;
      options: Array<{ id: string; label: string }>;
      open: boolean;
    }
  | { kind: 'research'; query: string; items: ResearchTranscriptItem[]; open: boolean; provider?: string; kindLabel?: ResearchBlockKind }
  | { kind: 'terminal'; command: string; output: string; open: boolean }
  | { kind: 'image'; path: string; open: boolean }
  | { kind: 'debug-reproduce'; steps: string[]; open: boolean }
  | {
      kind: 'lead-fan-out';
      planId: string;
      mode: string;
      leadName: string;
      title: string;
      queued: number;
      deferred: number;
      assignments: Array<{ role: string; goal: string }>;
      notes: string[];
    };
