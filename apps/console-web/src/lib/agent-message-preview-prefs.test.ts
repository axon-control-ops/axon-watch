import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  AGENT_MARKDOWN_PREVIEW_DEFAULT_KEY,
  AGENT_MARKDOWN_PREVIEW_MESSAGES_KEY,
  persistAgentMessagePreviewEnabled,
  readAgentMarkdownPreviewDefault,
  resolveAgentMessagePreviewEnabled,
} from './agent-message-preview-prefs';

describe('agent-message-preview-prefs', () => {
  beforeEach(() => {
    const storage = new Map<string, string>();
    vi.stubGlobal('window', {
      localStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
        removeItem: (key: string) => {
          storage.delete(key);
        },
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('defaults preview to enabled', () => {
    expect(readAgentMarkdownPreviewDefault()).toBe(true);
    expect(resolveAgentMessagePreviewEnabled('message-1', true)).toBe(true);
  });

  it('persists per-message preview preference', () => {
    persistAgentMessagePreviewEnabled('message-1', false);
    expect(resolveAgentMessagePreviewEnabled('message-1', true)).toBe(false);
    expect(window.localStorage.getItem(AGENT_MARKDOWN_PREVIEW_MESSAGES_KEY)).toContain('message-1');
  });

  it('persists global default preference', () => {
    window.localStorage.setItem(AGENT_MARKDOWN_PREVIEW_DEFAULT_KEY, 'false');
    expect(readAgentMarkdownPreviewDefault()).toBe(false);
  });
});
