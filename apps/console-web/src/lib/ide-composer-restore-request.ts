/** Cross-component request to switch Agent Dock composer mode after Edit/Resend. */

export type IdeComposerRestoreMode = 'ask' | 'plan' | 'agent' | 'kairo';

let pendingMode: IdeComposerRestoreMode | null = null;

export function requestIdeComposerMode(mode: IdeComposerRestoreMode): void {
  pendingMode = mode;
}

export function consumeIdeComposerModeRequest(): IdeComposerRestoreMode | null {
  const next = pendingMode;
  pendingMode = null;
  return next;
}
