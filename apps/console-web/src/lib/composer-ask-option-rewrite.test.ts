import { beforeEach, describe, expect, it } from 'vitest';

import { markQuestionAnswered, questionAnswerKey } from './answered-agent-questions';
import { rewriteComposerAskOptionAnswer } from './composer-ask-option-rewrite';

describe('rewriteComposerAskOptionAnswer', () => {
  beforeEach(() => {
    // markQuestionAnswered is session-global; use unique prompts per case.
  });

  it('rewrites a bare option digit to the Continue payload', () => {
    const askContent = [
      ':::ask How should I clear the canary gate?',
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    const rewritten = rewriteComposerAskOptionAnswer('3', [
      {
        message_id: 'msg_ask_rewrite',
        role: 'agent',
        content: askContent,
      },
    ]);
    expect(rewritten?.option.id).toBe('3');
    expect(rewritten?.content).toContain('Selected option 3: Force publish anyway');
    expect(rewritten?.content).toContain('(answer to: How should I clear the canary gate?)');
  });

  it('ignores bare digits when there is no open ask', () => {
    expect(
      rewriteComposerAskOptionAnswer('3', [
        { message_id: 'msg_plain', role: 'agent', content: 'All clear.' },
      ]),
    ).toBeNull();
  });

  it('ignores bare digits for already-marked asks', () => {
    const prompt = 'How should I clear the canary gate?';
    markQuestionAnswered('msg_marked_ask', prompt);
    expect(questionAnswerKey('msg_marked_ask', prompt)).toContain('msg_marked_ask');
    const askContent = [
      `:::ask ${prompt}`,
      '- 1 | Fix the tree and retry',
      '- 2 | Skip canary for now',
      '- 3 | Force publish anyway',
      ':::',
    ].join('\n');
    expect(
      rewriteComposerAskOptionAnswer('3', [
        {
          message_id: 'msg_marked_ask',
          role: 'agent',
          content: askContent,
        },
      ]),
    ).toBeNull();
  });
});
