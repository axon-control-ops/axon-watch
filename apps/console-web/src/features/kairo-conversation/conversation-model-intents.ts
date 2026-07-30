import { normalizeVoiceTranscript } from '../../lib/kairo-entity-labels';
import {
  cursorCatalogModelRows,
  cursorModelLabel,
  isCursorAutoModel,
  resolveCursorComposerModel,
  type CursorCatalogRow,
} from '../../lib/cursor-catalog-view';
import { CURSOR_PICKER_DEFAULT_MODEL } from '../../lib/cursor-picker-prefs';
import { DEFAULT_VAXON_MODEL_ID } from '../../lib/operator-presence-settings';

export type ConversationModelSwitchIntent = {
  kind: 'switch_composer_model';
  modelId: string;
  label: string;
  reply: string;
};

const CHANGE_BRAIN_TO_RE =
  /\b(?:change|switch|set|make)\s+(?:your\s+)?brain\s+(?:to|to\s+use)\s+(?!galaxy\b)(.+)/i;
const CHANGE_MODEL_TO_RE =
  /\b(?:change|switch|set|make)\s+(?:your\s+|the\s+)?(?:composer\s+)?model\s+(?:to|to\s+use)\s+(.+)/i;
const USE_AS_BRAIN_RE =
  /\b(?:use|pick|select)\s+(.+?)\s+(?:as|for)\s+(?:your\s+)?brain\b/i;
const USE_MODEL_RE =
  /^use\s+(auto|composer(?:\s+[\d.]+)?(?:\s+fast)?|grok(?:\s+[\d.]+)?(?:\s+fast)?|gpt[\d.\s\-]+(?:\s+high)?|claude[\w\s\-]+(?:\s+high)?)\b/i;

const MODEL_ALIASES: Record<string, string> = {
  auto: 'auto',
  composer: CURSOR_PICKER_DEFAULT_MODEL,
  'composer fast': 'composer-2.5-fast',
  'composer 2.5 fast': 'composer-2.5-fast',
  'composer 2.5': 'composer-2.5',
  'composer 2': 'composer-2.5',
  grok: 'cursor-grok-4.5-high-fast',
  'grok fast': 'cursor-grok-4.5-high-fast',
  'grok 4.5': 'cursor-grok-4.5-high-fast',
  'grok 4.5 fast': 'cursor-grok-4.5-high-fast',
  'cursor grok': 'cursor-grok-4.5-high-fast',
  'cursor grok 4.5': 'cursor-grok-4.5-high-fast',
  'cursor grok 4.5 fast': 'cursor-grok-4.5-high-fast',
  'gpt 5.4': 'gpt-5.4-high',
  'gpt 5.4 high': 'gpt-5.4-high',
  'gpt-5.4': 'gpt-5.4-high',
  'gpt 5': 'gpt-5.4-high',
  sonnet: 'claude-sonnet-5-thinking-high',
  'claude sonnet': 'claude-sonnet-5-thinking-high',
  opus: 'claude-opus-4-8-thinking-high',
  'claude opus': 'claude-opus-4-8-thinking-high',
  fable: 'claude-fable-5-thinking-high',
  'claude fable': 'claude-fable-5-thinking-high',
};

function normalizeModelPhrase(value: string): string {
  return normalizeVoiceTranscript(value)
    .trim()
    .toLowerCase()
    .replace(/[._/]+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\smodel$/i, '')
    .trim();
}

function extractModelPhrase(content: string): string | null {
  const trimmed = normalizeVoiceTranscript(content.trim());
  if (!trimmed) {
    return null;
  }

  for (const pattern of [CHANGE_BRAIN_TO_RE, CHANGE_MODEL_TO_RE, USE_AS_BRAIN_RE]) {
    const match = trimmed.match(pattern);
    const phrase = match?.[1]?.trim();
    if (phrase) {
      return phrase;
    }
  }

  const useMatch = trimmed.match(USE_MODEL_RE);
  if (useMatch?.[1]) {
    return useMatch[1].trim();
  }

  return null;
}

function scoreModelMatch(phrase: string, row: CursorCatalogRow): number {
  const needle = normalizeModelPhrase(phrase);
  if (!needle) {
    return 0;
  }

  const id = normalizeModelPhrase(row.id.replace(/-/g, ' '));
  const label = normalizeModelPhrase(row.label);
  const description = normalizeModelPhrase(row.description);

  if (needle === 'auto' && row.id === 'auto') {
    return 100;
  }
  if (normalizeModelPhrase(row.id) === needle || row.id === needle) {
    return 95;
  }
  if (label === needle || id === needle) {
    return 90;
  }
  if (label.includes(needle) || needle.includes(label)) {
    return 80;
  }
  if (id.includes(needle) || needle.includes(id)) {
    return 75;
  }
  if (`${label} ${description}`.includes(needle)) {
    return 60;
  }

  const phraseTokens = needle.split(' ').filter(Boolean);
  const haystack = `${id} ${label} ${description}`;
  const overlap = phraseTokens.filter((token) => haystack.includes(token)).length;
  return overlap >= 2 ? 50 + overlap : 0;
}

export function resolveModelIdFromPhrase(
  phrase: string,
  rows: CursorCatalogRow[],
): string | null {
  const normalized = normalizeModelPhrase(phrase);
  if (!normalized) {
    return null;
  }

  const alias = MODEL_ALIASES[normalized];
  if (alias) {
    return resolveCursorComposerModel(alias, rows);
  }

  const catalogRows = rows.length ? rows : [{ id: 'auto', label: 'Auto', description: '', available: true }];
  const models = cursorCatalogModelRows(catalogRows);
  const candidates = [
    ...catalogRows.filter((row) => row.id === 'auto'),
    ...models,
  ];

  let best: { id: string; score: number } | null = null;
  for (const row of candidates) {
    const score = scoreModelMatch(normalized, row);
    if (!best || score > best.score) {
      best = { id: row.id, score };
    }
  }

  if (!best || best.score < 50) {
    return null;
  }

  return resolveCursorComposerModel(best.id, rows);
}

export function resolveConversationModelSwitchIntent(
  content: string,
  rows: CursorCatalogRow[],
): ConversationModelSwitchIntent | null {
  const phrase = extractModelPhrase(content);
  if (!phrase) {
    return null;
  }

  const modelId = resolveModelIdFromPhrase(phrase, rows);
  if (!modelId) {
    return {
      kind: 'switch_composer_model',
      modelId: '',
      label: phrase,
      reply: `I couldn't match "${phrase}" to a Cursor model. Try Grok 4.5 Fast, Auto, Composer 2.5 Fast, or GPT-5.4 High.`,
    };
  }

  const label = cursorModelLabel(modelId, rows);
  const reply = isCursorAutoModel(modelId)
    ? `VAXON brain set to ${cursorModelLabel(DEFAULT_VAXON_MODEL_ID, rows)}. That is the operator-global default — Agent Dock keeps its own workspace model.`
    : `VAXON brain switched to ${label}. That is operator-global — Agent Dock keeps its own workspace model.`;

  return {
    kind: 'switch_composer_model',
    modelId,
    label,
    reply,
  };
}
