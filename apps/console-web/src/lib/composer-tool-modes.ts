/** Composer modes that create linked runs and may use tool execution. */
export type ToolCapableComposerMode = 'agent' | 'debug';

/** Modes that create a linked run for stop / resume / recovery. */
export type RunLinkedComposerMode = 'agent' | 'debug' | 'plan';

export function isToolCapableComposerMode(mode: string | null | undefined): boolean {
  const normalized = String(mode || '').trim().toLowerCase();
  return normalized === 'agent' || normalized === 'debug';
}

export function isRunLinkedComposerMode(mode: string | null | undefined): boolean {
  const normalized = String(mode || '').trim().toLowerCase();
  return normalized === 'agent' || normalized === 'debug' || normalized === 'plan';
}
