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
  | { kind: 'edit-failed'; path: string; reason: string }
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
    }
  | {
      kind: 'lead-standup';
      leadName: string;
      title: string;
      intro: string;
      bodyMarkdown: string;
      confidence: string | null;
      verificationNotice: string | null;
    }
  | {
      kind: 'lead-checkin';
      title: string;
      summary: string;
      findingCount: number;
      assignmentCount: number;
      findings: Array<{
        kind: string;
        kindLabel: string;
        title: string;
        owner: string;
        escalate: boolean;
        summary: string;
        detail: string;
      }>;
      nextSteps: string[];
      prompt: string;
      options: Array<{ id: string; label: string }>;
    };
