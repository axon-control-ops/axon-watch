import { describe, expect, it } from 'vitest';

import type { CursorCatalogRow } from '../../lib/cursor-catalog-view';
import {
  resolveConversationModelSwitchIntent,
  resolveModelIdFromPhrase,
} from './conversation-model-intents';

const ROWS: CursorCatalogRow[] = [
  { id: 'auto', label: 'Auto', description: 'Cursor default', available: true },
  { id: 'composer-2.5-fast', label: 'Composer 2.5 Fast', description: 'Fast', available: true },
  { id: 'composer-2.5', label: 'Composer 2.5', description: 'Composer', available: true },
  { id: 'gpt-5.4-high', label: 'GPT-5.4 High', description: 'GPT', available: true },
  {
    id: 'cursor-grok-4.5-high-fast',
    label: 'Cursor Grok 4.5 Fast',
    description: 'Grok',
    available: true,
  },
  {
    id: 'claude-sonnet-5-thinking-high',
    label: 'Claude Sonnet 5 Thinking High',
    description: 'Sonnet',
    available: true,
  },
];

describe('resolveConversationModelSwitchIntent', () => {
  it('switches brain to a named model from voice phrasing', () => {
    expect(resolveConversationModelSwitchIntent('change your brain to GPT 5.4 high', ROWS)).toEqual({
      kind: 'switch_composer_model',
      modelId: 'gpt-5.4-high',
      label: 'GPT-5.4 High',
      reply:
        'VAXON brain switched to GPT-5.4 High. That is operator-global — Agent Dock keeps its own workspace model.',
    });
  });

  it('switches to Grok 4.5 Fast from short phrasing', () => {
    // cursorModelLabel() intentionally drops the redundant "Cursor" catalog
    // prefix on the model chip — the family chip elsewhere already says Cursor.
    expect(resolveConversationModelSwitchIntent('change brain to grok fast', ROWS)).toEqual({
      kind: 'switch_composer_model',
      modelId: 'cursor-grok-4.5-high-fast',
      label: 'Grok 4.5 Fast',
      reply:
        'VAXON brain switched to Grok 4.5 Fast. That is operator-global — Agent Dock keeps its own workspace model.',
    });
  });

  it('switches composer model phrasing', () => {
    expect(resolveConversationModelSwitchIntent('switch model to Composer 2.5 Fast', ROWS)).toEqual({
      kind: 'switch_composer_model',
      modelId: 'composer-2.5-fast',
      label: 'Composer 2.5 Fast',
      reply:
        'VAXON brain switched to Composer 2.5 Fast. That is operator-global — Agent Dock keeps its own workspace model.',
    });
  });

  it('supports use-as-brain phrasing', () => {
    expect(resolveConversationModelSwitchIntent('use Claude Sonnet as your brain', ROWS)?.modelId).toBe(
      'claude-sonnet-5-thinking-high',
    );
  });

  it('sets auto without matching brain galaxy navigation', () => {
    const autoIntent = resolveConversationModelSwitchIntent('set brain to auto', ROWS);
    expect(autoIntent?.modelId).toBe('auto');
    expect(autoIntent?.reply).toContain('operator-global default');
    expect(resolveConversationModelSwitchIntent('switch to brain galaxy', ROWS)).toBeNull();
  });

  it('returns a helpful reply when the model is unknown', () => {
    const intent = resolveConversationModelSwitchIntent('change brain to imaginary-model', ROWS);
    expect(intent?.modelId).toBe('');
    expect(intent?.reply).toContain("couldn't match");
  });
});

describe('resolveModelIdFromPhrase', () => {
  it('resolves common aliases', () => {
    expect(resolveModelIdFromPhrase('composer fast', ROWS)).toBe('composer-2.5-fast');
    expect(resolveModelIdFromPhrase('gpt 5.4', ROWS)).toBe('gpt-5.4-high');
    expect(resolveModelIdFromPhrase('grok 4.5 fast', ROWS)).toBe('cursor-grok-4.5-high-fast');
  });
});
