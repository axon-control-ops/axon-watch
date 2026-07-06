const VISIBLE_MODELS_KEY = 'axon-watch.cursorPickerVisibleModels';

export const CURSOR_PICKER_CURATED_IDS = [
  'composer-2.5',
  'composer-2.5-fast',
  'claude-4.6-sonnet-medium-thinking',
  'claude-fable-5-thinking-high',
  'claude-opus-4-8-thinking-high',
  'gpt-5.3-codex',
  'gpt-5.4',
  'gpt-5.4-high-fast',
  'gpt-5.5-medium',
] as const;

function uniqueStrings(values: string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const value of values) {
    const next = value.trim();
    if (!next || seen.has(next)) {
      continue;
    }
    seen.add(next);
    output.push(next);
  }
  return output;
}

export function readCursorPickerVisibleModelIds(): string[] {
  try {
    const raw = localStorage.getItem(VISIBLE_MODELS_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return uniqueStrings(parsed.map((value) => String(value ?? '')));
  } catch {
    return [];
  }
}

export function writeCursorPickerVisibleModelIds(modelIds: string[]): string[] {
  const next = uniqueStrings(modelIds);
  try {
    localStorage.setItem(VISIBLE_MODELS_KEY, JSON.stringify(next));
  } catch {
    // Ignore quota failures.
  }
  return next;
}

export function cursorPickerExplicitVisibleModelSet(modelIds: string[]): Set<string> {
  const explicit = new Set<string>();
  for (const id of modelIds) {
    if (!id || id === 'auto') {
      continue;
    }
    if ((CURSOR_PICKER_CURATED_IDS as readonly string[]).includes(id)) {
      continue;
    }
    explicit.add(id);
  }
  return explicit;
}

export function toggleCursorPickerVisibleModel(
  modelId: string,
  currentIds: string[],
): string[] {
  const id = modelId.trim();
  if (!id || id === 'auto') {
    return currentIds;
  }
  const explicit = cursorPickerExplicitVisibleModelSet(currentIds);
  if (explicit.has(id)) {
    explicit.delete(id);
  } else {
    explicit.add(id);
  }
  return writeCursorPickerVisibleModelIds([...explicit]);
}

export function isCursorPickerCuratedModel(modelId: string): boolean {
  const id = modelId.trim();
  return Boolean(id) && (CURSOR_PICKER_CURATED_IDS as readonly string[]).includes(id);
}
