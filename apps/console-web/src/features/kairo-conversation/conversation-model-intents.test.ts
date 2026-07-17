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
      reply: 'Brain switched to GPT-5.4 High. The orb and Agent dock now use that model.',
    });
  });

  it('switches composer model phrasing', () => {
    expect(resolveConversationModelSwitchIntent('switch model to Composer 2.5 Fast', ROWS)).toEqual({
      kind: 'switch_composer_model',
      modelId: 'composer-2.5-fast',
      label: 'Composer 2.5 Fast',
      reply: 'Brain switched to Composer 2.5 Fast. The orb and Agent dock now use that model.',
    });
  });

  it('supports use-as-brain phrasing', () => {
    expect(resolveConversationModelSwitchIntent('use Claude Sonnet as your brain', ROWS)?.modelId).toBe(
      'claude-sonnet-5-thinking-high',
    );
  });

  it('sets auto without matching brain galaxy navigation', () => {
    expect(resolveConversationModelSwitchIntent('set brain to auto', ROWS)?.modelId).toBe('auto');
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
  });
});
