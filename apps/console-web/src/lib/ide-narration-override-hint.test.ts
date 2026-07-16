import { describe, expect, it } from 'vitest';

import {
  consumeIdeNarrationOverrideHint,
  IDE_NARRATION_OVERRIDE_HINT_KEY,
  IDE_NARRATION_OVERRIDE_HINT_MESSAGE,
  shouldSurfaceIdeNarrationOverrideHint,
} from './ide-narration-override-hint';

describe('ide-narration-override-hint', () => {
  it('detects minimal narration muted by IDE quiet', () => {
    expect(
      shouldSurfaceIdeNarrationOverrideHint({
        layoutMode: 'ide',
        idePresenceProfile: 'quiet',
        configuredNarration: 'minimal',
        effectiveNarration: 'off',
      }),
    ).toBe(true);
    expect(
      shouldSurfaceIdeNarrationOverrideHint({
        layoutMode: 'ide',
        idePresenceProfile: 'quiet',
        configuredNarration: 'conversational',
        effectiveNarration: 'conversational',
      }),
    ).toBe(false);
  });

  it('consumes the hint only once per session', () => {
    const storage = new Map<string, string>();
    const session = {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
    };
    const input = {
      layoutMode: 'ide' as const,
      idePresenceProfile: 'quiet' as const,
      configuredNarration: 'minimal' as const,
      effectiveNarration: 'off' as const,
    };

    expect(consumeIdeNarrationOverrideHint(input, session)).toBe(
      IDE_NARRATION_OVERRIDE_HINT_MESSAGE,
    );
    expect(storage.get(IDE_NARRATION_OVERRIDE_HINT_KEY)).toBe('1');
    expect(consumeIdeNarrationOverrideHint(input, session)).toBeNull();
  });
});
