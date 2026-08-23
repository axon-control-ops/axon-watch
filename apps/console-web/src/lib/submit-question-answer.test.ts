import { beforeEach, describe, expect, it } from 'vitest';

import { isQuestionMarkedAnswered } from './answered-agent-questions';
import { submitQuestionAnswer } from './submit-question-answer';

const storage = new Map<string, string>();

beforeEach(() => {
  storage.clear();
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key),
    },
  });
});

describe('submitQuestionAnswer', () => {
  it('marks a question answered only after a successful send', async () => {
    const prompt = 'Which validation should run?';
    const messageId = 'msg_submit_success';

    await submitQuestionAnswer(
      {
        openIdeComposerWithDraft: () => undefined,
        submitIdeComposer: async () => true,
      },
      {
        workspaceId: 'workspace_test',
        messageId,
        prompt,
        option: { id: '4', label: 'All of the above' },
      },
    );

    expect(isQuestionMarkedAnswered(messageId, prompt)).toBe(true);
  });

  it('keeps the card unanswered when the send is blocked', async () => {
    const prompt = 'Which validation should run after failure?';
    const messageId = 'msg_submit_failure';

    await expect(
      submitQuestionAnswer(
        {
          openIdeComposerWithDraft: () => undefined,
          submitIdeComposer: async () => false,
        },
        {
          workspaceId: 'workspace_test',
          messageId,
          prompt,
          option: { id: '4', label: 'All of the above' },
        },
      ),
    ).rejects.toThrow('Unable to send this choice');

    expect(isQuestionMarkedAnswered(messageId, prompt)).toBe(false);
  });
});
