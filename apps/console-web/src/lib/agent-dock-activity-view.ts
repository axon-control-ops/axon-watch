import type { AgentExecutionAccess } from './agent-execution-access-prefs';
import type { AgentStreamCounts } from './agent-stream-incremental';

export type IdeComposerActivity = {
  label: string;
  mode: 'ask' | 'plan' | 'agent';
  executionAccess: AgentExecutionAccess;
  /** Operator message that started the current composer turn (for KAIRO narration). */
  operatorPrompt?: string;
  /** Full streaming body behind a truncated live label (thinking/tool text). */
  liveBodyFull?: string | null;
  /** First complete sentence block for voice playback. */
  liveBodySpoken?: string | null;
  liveBodyTruncated?: boolean;
  /** Incremental stream header counts — avoids full transcript scans during SSE. */
  streamCounts?: AgentStreamCounts;
};

export function buildIdeComposerActivityLabel(
  mode: 'ask' | 'plan' | 'agent',
  executionAccess: AgentExecutionAccess,
): string {
  if (mode === 'agent' && executionAccess === 'full') {
    return 'Full Access — contacting Cursor/Codex runtime…';
  }
  if (mode === 'agent') {
    return 'Agent — contacting runtime…';
  }
  if (mode === 'plan') {
    return 'Plan — generating outline…';
  }
  return 'Ask — generating reply…';
}

export function buildIdeStreamActivityLabel(executionAccess: AgentExecutionAccess): string {
  if (executionAccess === 'full') {
    return 'Full Access — streaming runtime output…';
  }
  return 'Streaming agent reply…';
}

export const FULL_ACCESS_CONSENT_LINES = [
  'Full Access lets the Agent edit files, run shell commands, and change your workspace.',
  'This consent is the approval: Agent turns execute immediately, with no per-run Approve step.',
  'It lasts for this session only. Switch back to Consultative at any time to stop tool execution.',
] as const;
