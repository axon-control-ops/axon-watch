import { describe, expect, it } from 'vitest';

import {
  recordAgentComposerHistoryEntry,
  shouldRecallNextAgentComposerHistory,
  shouldRecallPreviousAgentComposerHistory,
  stepAgentComposerHistory,
} from './agent-dock-composer-history';

describe('agent dock composer history', () => {
  it('stores newest unique prompts first', () => {
    expect(
      recordAgentComposerHistoryEntry(
        ['second prompt', 'first prompt'],
        ' first prompt ',
      ),
    ).toEqual(['first prompt', 'second prompt']);
  });

  it('recalls previous history only from the first line', () => {
    expect(
      shouldRecallPreviousAgentComposerHistory({
        key: 'ArrowUp',
        shiftKey: false,
        selectionStart: 0,
        selectionEnd: 0,
        value: '',
      }),
    ).toBe(true);

    expect(
      shouldRecallPreviousAgentComposerHistory({
        key: 'ArrowUp',
        shiftKey: false,
        selectionStart: 7,
        selectionEnd: 7,
        value: 'line 1\nline 2',
      }),
    ).toBe(false);
  });

  it('steps backward and forward through history while preserving scratch draft', () => {
    const entries = ['latest', 'older'];
    const first = stepAgentComposerHistory({
      entries,
      index: -1,
      scratch: '',
      currentDraft: 'scratch draft',
      direction: 'previous',
    });
    expect(first).toEqual({
      index: 0,
      scratch: 'scratch draft',
      draft: 'latest',
    });

    const second = stepAgentComposerHistory({
      entries,
      index: first.index,
      scratch: first.scratch,
      currentDraft: first.draft,
      direction: 'previous',
    });
    expect(second).toEqual({
      index: 1,
      scratch: 'scratch draft',
      draft: 'older',
    });

    const third = stepAgentComposerHistory({
      entries,
      index: second.index,
      scratch: second.scratch,
      currentDraft: second.draft,
      direction: 'next',
    });
    expect(third).toEqual({
      index: 0,
      scratch: 'scratch draft',
      draft: 'latest',
    });

    const fourth = stepAgentComposerHistory({
      entries,
      index: third.index,
      scratch: third.scratch,
      currentDraft: third.draft,
      direction: 'next',
    });
    expect(fourth).toEqual({
      index: -1,
      scratch: '',
      draft: 'scratch draft',
    });
  });

  it('allows ArrowDown only while browsing history', () => {
    expect(
      shouldRecallNextAgentComposerHistory(
        {
          key: 'ArrowDown',
          shiftKey: false,
          selectionStart: 3,
          selectionEnd: 3,
          value: 'foo',
        },
        true,
      ),
    ).toBe(true);

    expect(
      shouldRecallNextAgentComposerHistory(
        {
          key: 'ArrowDown',
          shiftKey: false,
          selectionStart: 3,
          selectionEnd: 3,
          value: 'foo',
        },
        false,
      ),
    ).toBe(false);
  });
});
