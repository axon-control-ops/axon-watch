import type { AgentExecutionAccess } from './agent-execution-access-prefs';

export type IdeComposerModeTone = 'ask' | 'plan' | 'agent' | 'debug';

export type ThreadStatusStripTone =
  | 'ask'
  | 'plan'
  | 'agent'
  | 'agent-full'
  | 'debug'
  | 'debug-full';

export function resolveThreadStatusStripTone(
  mode: IdeComposerModeTone | null | undefined,
  executionAccess: AgentExecutionAccess | null | undefined,
): ThreadStatusStripTone {
  const resolved = mode ?? 'agent';
  const full = executionAccess === 'full';
  if (resolved === 'ask') {
    return 'ask';
  }
  if (resolved === 'plan') {
    return 'plan';
  }
  if (resolved === 'debug') {
    return full ? 'debug-full' : 'debug';
  }
  return full ? 'agent-full' : 'agent';
}

export function threadStatusStripClassNames(input: {
  tone: ThreadStatusStripTone;
  streaming: boolean;
}): string[] {
  const classes = [
    'conversation-seam__item--thread-status',
    `conversation-seam__item--thread-status--${input.tone}`,
  ];
  if (input.streaming) {
    classes.push('conversation-seam__item--thread-status--streaming');
  }
  return classes;
}
