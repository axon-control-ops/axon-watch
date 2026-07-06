import { describe, expect, it } from 'vitest';

import { shouldSubmitAgentDockComposer } from './agent-dock-composer-input';

describe('agent dock composer input', () => {
  it('submits on plain Enter', () => {
    expect(
      shouldSubmitAgentDockComposer({
        key: 'Enter',
        shiftKey: false,
        isComposing: false,
      }),
    ).toBe(true);
  });

  it('keeps Shift+Enter for multiline drafts', () => {
    expect(
      shouldSubmitAgentDockComposer({
        key: 'Enter',
        shiftKey: true,
        isComposing: false,
      }),
    ).toBe(false);
  });

  it('does not submit while IME composition is active', () => {
    expect(
      shouldSubmitAgentDockComposer({
        key: 'Enter',
        shiftKey: false,
        isComposing: true,
      }),
    ).toBe(false);
  });
});
