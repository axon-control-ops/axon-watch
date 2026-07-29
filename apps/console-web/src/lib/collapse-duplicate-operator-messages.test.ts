import { describe, expect, it } from 'vitest';

import { collapseConsecutiveDuplicateOperatorMessages } from './collapse-duplicate-operator-messages';

describe('collapseConsecutiveDuplicateOperatorMessages', () => {
  it('collapses consecutive identical operator prompts from Continue', () => {
    const messages = collapseConsecutiveDuplicateOperatorMessages([
      {
        role: 'operator',
        content: 'Continue - I also attached the CSV',
        attachments: [{ attachment_id: 'att_1' }],
      },
      {
        role: 'operator',
        content: 'Continue - I also attached the CSV',
        attachments: [{ attachment_id: 'att_1' }],
      },
      { role: 'agent', content: 'working' },
    ]);

    expect(messages).toHaveLength(2);
    expect(messages[0]?.role).toBe('operator');
    expect(messages[1]?.role).toBe('agent');
  });

  it('keeps distinct consecutive operator prompts', () => {
    const messages = collapseConsecutiveDuplicateOperatorMessages([
      { role: 'operator', content: 'first' },
      { role: 'operator', content: 'second' },
    ]);
    expect(messages).toHaveLength(2);
  });

  it('keeps same text when attachments differ', () => {
    const messages = collapseConsecutiveDuplicateOperatorMessages([
      { role: 'operator', content: 'same', attachments: [{ attachment_id: 'a' }] },
      { role: 'operator', content: 'same', attachments: [{ attachment_id: 'b' }] },
    ]);
    expect(messages).toHaveLength(2);
  });
});
