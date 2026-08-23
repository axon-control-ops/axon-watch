import type { AgentExecutionAccess } from './agent-execution-access-prefs';
import type { AgentStreamCounts } from './agent-stream-incremental';

export type IdeComposerActivity = {
  label: string;
  mode: 'ask' | 'plan' | 'agent' | 'debug';
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
  mode: 'ask' | 'plan' | 'agent' | 'debug',
  executionAccess: AgentExecutionAccess,
  runtimeFamily?: string | null,
): string {
  const family = String(runtimeFamily ?? '').trim().toLowerCase();
  const runtimePhrase =
    family === 'cursor'
      ? 'Cursor runtime'
      : family === 'claude'
        ? 'Claude runtime'
        : family === 'codex'
          ? 'Codex runtime'
          : 'runtime';
  if (mode === 'debug' && executionAccess === 'full') {
    return `Debug · Full Access — contacting ${runtimePhrase}…`;
  }
  if (mode === 'debug') {
    return 'Debug — contacting runtime…';
  }
  if (mode === 'agent' && executionAccess === 'full') {
    return `Full Access — contacting ${runtimePhrase}…`;
  }
  if (mode === 'agent') {
    return 'Agent — contacting runtime…';
  }
  if (mode === 'plan') {
    return 'Plan — generating outline…';
  }
  return 'Ask — generating reply…';
}

export function buildIdeStreamActivityLabel(
  executionAccess: AgentExecutionAccess,
  mode: 'ask' | 'plan' | 'agent' | 'debug' = 'agent',
): string {
  if (mode === 'ask') {
    return 'Ask — streaming reply…';
  }
  if (mode === 'plan') {
    return 'Plan — streaming outline…';
  }
  if (mode === 'debug' && executionAccess === 'full') {
    return 'Debug · Full Access — streaming runtime output…';
  }
  if (mode === 'debug') {
    return 'Debug — streaming runtime output…';
  }
  if (executionAccess === 'full') {
    return 'Full Access — streaming runtime output…';
  }
  return 'Agent — streaming runtime output…';
}

export const FULL_ACCESS_CONSENT_LINES = [
  'Full Access lets Agent and Debug edit files, run shell commands, and change your workspace.',
  'This consent is the approval: tool-capable turns execute immediately, with no per-run Approve step.',
  'It lasts for this session only. Switch back to Consultative at any time to stop tool execution.',
] as const;
