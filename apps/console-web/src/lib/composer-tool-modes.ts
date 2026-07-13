/** Composer modes that create linked runs and may use tool execution. */
export type ToolCapableComposerMode = 'agent' | 'debug';

export function isToolCapableComposerMode(mode: string | null | undefined): boolean {
  const normalized = String(mode || '').trim().toLowerCase();
  return normalized === 'agent' || normalized === 'debug';
}
