import { describe, expect, it } from 'vitest';

import { groupIdeConversationTurns } from './group-ide-conversation-turns';
import type { OperatorThreadEntry } from './operator-thread';

function msg(
  role: OperatorThreadEntry['role'],
  id: string,
  content = role,
): OperatorThreadEntry {
  return {
    message_id: id,
    role,
    content,
    created_at: '2026-07-29T00:00:00Z',
  };
}

describe('groupIdeConversationTurns', () => {
  it('scopes agent replies under the preceding operator prompt', () => {
    const turns = groupIdeConversationTurns([
      msg('operator', 'o1', 'first'),
      msg('agent', 'a1', 'reply1'),
      msg('agent', 'a2', 'reply2'),
      msg('operator', 'o2', 'second'),
      msg('agent', 'a3', 'reply3'),
    ]);

    expect(turns).toHaveLength(2);
    expect(turns[0]?.prompt?.message_id).toBe('o1');
    expect(turns[0]?.replies.map((item) => item.message_id)).toEqual(['a1', 'a2']);
    expect(turns[1]?.prompt?.message_id).toBe('o2');
    expect(turns[1]?.replies.map((item) => item.message_id)).toEqual(['a3']);
  });

  it('keeps orphan agent messages in a prompt-less turn', () => {
    const turns = groupIdeConversationTurns([msg('agent', 'a0', 'solo')]);
    expect(turns).toHaveLength(1);
    expect(turns[0]?.prompt).toBeNull();
    expect(turns[0]?.replies[0]?.message_id).toBe('a0');
  });

  it('replaces the previous turn when the same YOU prompt is resent', () => {
    const turns = groupIdeConversationTurns([
      msg('operator', 'o1', 'I think option 2 is the best - what do you think?'),
      msg('agent', 'a1', 'here is option 2'),
      msg('operator', 'o2', 'I think option 2 is the best - what do you think?'),
      msg('agent', 'a2', 'regenerated'),
    ]);

    expect(turns).toHaveLength(1);
    expect(turns[0]?.prompt?.message_id).toBe('o2');
    expect(turns[0]?.replies.map((item) => item.message_id)).toEqual(['a2']);
  });

  it('keeps distinct prompts even when text matches a non-adjacent turn', () => {
    const turns = groupIdeConversationTurns([
      msg('operator', 'o1', 'same'),
      msg('agent', 'a1', 'first'),
      msg('operator', 'o2', 'different'),
      msg('agent', 'a2', 'middle'),
      msg('operator', 'o3', 'same'),
      msg('agent', 'a3', 'again'),
    ]);

    expect(turns).toHaveLength(3);
    expect(turns.map((turn) => turn.prompt?.message_id)).toEqual(['o1', 'o2', 'o3']);
  });
});
