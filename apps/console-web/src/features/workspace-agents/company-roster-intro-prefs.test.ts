import { describe, expect, it } from 'vitest';

import {
  calendarDayKey,
  hasSpokenIntroToday,
  markIntroSpokenToday,
  readIntroDayMap,
  resolveTalkSpeakMode,
  COMPANY_ROSTER_INTRO_PREFS_KEY,
} from './company-roster-intro-prefs';

class MemoryStorage implements Pick<Storage, 'getItem' | 'setItem'> {
  private readonly data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.has(key) ? (this.data.get(key) as string) : null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

describe('company-roster-intro-prefs', () => {
  it('treats missing prefs as intro-needed', () => {
    const storage = new MemoryStorage();
    expect(hasSpokenIntroToday('e1', new Date('2026-07-14T10:00:00'), storage)).toBe(false);
    expect(resolveTalkSpeakMode('e1', new Date('2026-07-14T10:00:00'), storage)).toBe('intro');
  });

  it('marks intro for today and switches to callback', () => {
    const storage = new MemoryStorage();
    const now = new Date('2026-07-14T10:00:00');
    markIntroSpokenToday('e1', now, storage);
    expect(hasSpokenIntroToday('e1', now, storage)).toBe(true);
    expect(resolveTalkSpeakMode('e1', now, storage)).toBe('callback');
    expect(readIntroDayMap(storage)).toEqual({ e1: '2026-07-14' });
    expect(storage.getItem(COMPANY_ROSTER_INTRO_PREFS_KEY)).toContain('2026-07-14');
  });

  it('resets intro on a new calendar day', () => {
    const storage = new MemoryStorage();
    markIntroSpokenToday('e1', new Date('2026-07-14T22:00:00'), storage);
    expect(hasSpokenIntroToday('e1', new Date('2026-07-15T01:00:00'), storage)).toBe(false);
    expect(resolveTalkSpeakMode('e1', new Date('2026-07-15T01:00:00'), storage)).toBe('intro');
  });

  it('formats local calendar day keys', () => {
    expect(calendarDayKey(new Date(2026, 6, 14, 8, 0, 0))).toBe('2026-07-14');
  });
});
