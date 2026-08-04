const VISIBLE_MODELS_KEY = 'axon-watch.claudePickerVisibleModels';

/** Sonnet is Claude Code's own default — always shown as the primary pick. */
export const CLAUDE_PICKER_PRIMARY_IDS = ['sonnet'] as const;

export const CLAUDE_PICKER_DEFAULT_MODEL = 'sonnet';

export const CLAUDE_PICKER_CURATED_IDS = [
  ...CLAUDE_PICKER_PRIMARY_IDS,
  'opus',
  'haiku',
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

export function readClaudePickerVisibleModelIds(): string[] {
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

export function writeClaudePickerVisibleModelIds(modelIds: string[]): string[] {
  const next = uniqueStrings(modelIds);
  try {
    localStorage.setItem(VISIBLE_MODELS_KEY, JSON.stringify(next));
  } catch {
    // Ignore quota failures.
  }
  return next;
}

export function claudePickerExplicitVisibleModelSet(modelIds: string[]): Set<string> {
  const explicit = new Set<string>();
  for (const id of modelIds) {
    if (!id || id === 'auto') {
      continue;
    }
    if ((CLAUDE_PICKER_CURATED_IDS as readonly string[]).includes(id)) {
      continue;
    }
    explicit.add(id);
  }
  return explicit;
}

export function toggleClaudePickerVisibleModel(
  modelId: string,
  currentIds: string[],
): string[] {
  const id = modelId.trim();
  if (!id || id === 'auto') {
    return currentIds;
  }
  const explicit = claudePickerExplicitVisibleModelSet(currentIds);
  if (explicit.has(id)) {
    explicit.delete(id);
  } else {
    explicit.add(id);
  }
  return writeClaudePickerVisibleModelIds([...explicit]);
}

export function isClaudePickerCuratedModel(modelId: string): boolean {
  const id = modelId.trim();
  return Boolean(id) && (CLAUDE_PICKER_CURATED_IDS as readonly string[]).includes(id);
}
