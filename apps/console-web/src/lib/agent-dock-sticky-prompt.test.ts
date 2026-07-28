import { describe, expect, it } from 'vitest';

import { resolveAgentDockStickyPrompt } from './agent-dock-sticky-prompt';

describe('resolveAgentDockStickyPrompt', () => {
  it('pins the latest operator message', () => {
    expect(
      resolveAgentDockStickyPrompt({
        threadMessages: [
          { role: 'operator', content: 'older' },
          { role: 'agent', content: 'reply' },
          { role: 'operator', content: 'Oi assign all the agents' },
          { role: 'agent', content: 'working' },
        ],
      }),
    ).toBe('Oi assign all the agents');
  });

  it('falls back to in-flight composer activity prompt', () => {
    expect(
      resolveAgentDockStickyPrompt({
        threadMessages: [{ role: 'agent', content: 'still streaming' }],
        activityPrompt: 'new ask',
      }),
    ).toBe('new ask');
  });
});
