import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  appendBriefingVoiceTranscriptEntry,
  persistBriefingVoiceTranscript,
  readBriefingVoiceTranscript,
} from './briefing-voice-transcript';

describe('briefing voice transcript', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('appends newest spoken briefing entries first', () => {
    const storage = new Map<string, string>();
    vi.stubGlobal('sessionStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
    });

    appendBriefingVoiceTranscriptEntry({ message: 'First spoken line' });
    appendBriefingVoiceTranscriptEntry({ message: 'Second spoken line' });

    const entries = readBriefingVoiceTranscript();
    expect(entries).toHaveLength(2);
    expect(entries[0]?.message).toBe('Second spoken line');
    expect(entries[1]?.message).toBe('First spoken line');
  });

  it('caps the transcript list to the configured limit', () => {
    const entries = Array.from({ length: 8 }, (_, index) => ({
      id: `entry_${index}`,
      createdAt: `2026-07-11T08:0${index}:00Z`,
      message: `Line ${index}`,
      workspaceId: null,
    }));

    const storage = new Map<string, string>();
    vi.stubGlobal('sessionStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
    });

    const persisted = persistBriefingVoiceTranscript(entries);
    expect(persisted).toHaveLength(6);
    expect(persisted[0]?.message).toBe('Line 0');
    expect(persisted.at(-1)?.message).toBe('Line 5');
  });
});
