import type { KairoNarrationLevel } from '../contracts/canonical';

import type { IdePresenceProfile } from './ide-presence-profile';

export const IDE_NARRATION_OVERRIDE_HINT_KEY = 'axon-x:ide-narration-override-hint-shown';

export const IDE_NARRATION_OVERRIDE_HINT_MESSAGE =
  'Voice is silent in IDE Quiet while narration is Minimal. Switch to Conversational or enable the IDE voice strip in settings.';

export function shouldSurfaceIdeNarrationOverrideHint(input: {
  layoutMode: 'operator' | 'ide';
  idePresenceProfile: IdePresenceProfile;
  configuredNarration: KairoNarrationLevel;
  effectiveNarration: KairoNarrationLevel;
}): boolean {
  if (input.layoutMode !== 'ide' || input.idePresenceProfile !== 'quiet') {
    return false;
  }
  if (input.configuredNarration !== 'minimal') {
    return false;
  }
  return input.effectiveNarration === 'off';
}

let activeRuntimeHint: string | null = null;

export function getActiveIdeNarrationOverrideHint(): string | null {
  return activeRuntimeHint;
}

export function clearActiveIdeNarrationOverrideHint(): void {
  activeRuntimeHint = null;
}

export function consumeIdeNarrationOverrideHint(
  input: Parameters<typeof shouldSurfaceIdeNarrationOverrideHint>[0],
  storage: Pick<Storage, 'getItem' | 'setItem'> = sessionStorage,
): string | null {
  if (!shouldSurfaceIdeNarrationOverrideHint(input)) {
    return null;
  }
  if (storage.getItem(IDE_NARRATION_OVERRIDE_HINT_KEY) === '1') {
    return null;
  }
  storage.setItem(IDE_NARRATION_OVERRIDE_HINT_KEY, '1');
  activeRuntimeHint = IDE_NARRATION_OVERRIDE_HINT_MESSAGE;
  return IDE_NARRATION_OVERRIDE_HINT_MESSAGE;
}
