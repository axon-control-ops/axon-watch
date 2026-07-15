/** Per-employee daily intro: first talk click of the day is formal; later clicks are casual. */

export const COMPANY_ROSTER_INTRO_PREFS_KEY = 'axon-x:company-roster-intro-day-v1';

export type CompanyRosterIntroDayMap = Record<string, string>;

export function calendarDayKey(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function readIntroDayMap(
  storage: Pick<Storage, 'getItem'> | null | undefined =
    typeof localStorage !== 'undefined' ? localStorage : null,
): CompanyRosterIntroDayMap {
  if (!storage) {
    return {};
  }
  try {
    const raw = storage.getItem(COMPANY_ROSTER_INTRO_PREFS_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return {};
    }
    const out: CompanyRosterIntroDayMap = {};
    for (const [employeeId, day] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof employeeId === 'string' && typeof day === 'string' && day.trim()) {
        out[employeeId] = day.trim();
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function writeIntroDayMap(
  map: CompanyRosterIntroDayMap,
  storage: Pick<Storage, 'setItem'> | null | undefined =
    typeof localStorage !== 'undefined' ? localStorage : null,
): void {
  if (!storage) {
    return;
  }
  storage.setItem(COMPANY_ROSTER_INTRO_PREFS_KEY, JSON.stringify(map));
}

export function hasSpokenIntroToday(
  employeeId: string,
  now: Date = new Date(),
  storage: Pick<Storage, 'getItem'> | null | undefined =
    typeof localStorage !== 'undefined' ? localStorage : null,
): boolean {
  const id = employeeId.trim();
  if (!id) {
    return false;
  }
  const map = readIntroDayMap(storage);
  return map[id] === calendarDayKey(now);
}

export function markIntroSpokenToday(
  employeeId: string,
  now: Date = new Date(),
  storage: Pick<Storage, 'getItem' | 'setItem'> | null | undefined =
    typeof localStorage !== 'undefined' ? localStorage : null,
): void {
  const id = employeeId.trim();
  if (!id || !storage) {
    return;
  }
  const today = calendarDayKey(now);
  const map = readIntroDayMap(storage);
  if (map[id] === today) {
    return;
  }
  map[id] = today;
  // Drop stale days so the map does not grow forever across many employees.
  for (const [key, day] of Object.entries(map)) {
    if (day !== today) {
      delete map[key];
    }
  }
  writeIntroDayMap(map, storage);
}

export function resolveTalkSpeakMode(
  employeeId: string,
  now: Date = new Date(),
  storage: Pick<Storage, 'getItem'> | null | undefined =
    typeof localStorage !== 'undefined' ? localStorage : null,
): 'intro' | 'callback' {
  return hasSpokenIntroToday(employeeId, now, storage) ? 'callback' : 'intro';
}
