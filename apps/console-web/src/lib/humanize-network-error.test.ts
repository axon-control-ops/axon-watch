import { describe, expect, it } from 'vitest';

import { humanizeNetworkError } from './humanize-network-error';

describe('humanizeNetworkError', () => {
  it('explains bare Failed to fetch', () => {
    expect(humanizeNetworkError(new TypeError('Failed to fetch'), { action: 'Chat send' })).toContain(
      'could not reach the control plane',
    );
    expect(humanizeNetworkError(new TypeError('Failed to fetch'), { action: 'Chat send' })).toContain(
      'check-health.sh is green',
    );
  });

  it('passes through labeled timeouts', () => {
    expect(
      humanizeNetworkError(new Error('chat message submit failed: timed out after 60000ms'), {
        action: 'Chat send',
      }),
    ).toContain('timed out after 60000ms');
  });

  it('keeps ApiRequestError-style labels', () => {
    expect(
      humanizeNetworkError(new Error('chat message submit failed: mutating API rate limit exceeded'), {
        action: 'Chat send',
      }),
    ).toBe('chat message submit failed: mutating API rate limit exceeded');
  });

  it('explains control-plane 503 soft failures', () => {
    expect(
      humanizeNetworkError(new Error('chat message submit failed: control-plane unavailable'), {
        action: 'Chat send',
      }),
    ).toContain('brief control-plane gap');
  });

  it('explains step-up confirmation failures', () => {
    expect(
      humanizeNetworkError(new Error('agent chat failed: step-up confirmation required'), {
        action: 'Chat send',
      }),
    ).toContain('Full Access step-up');
  });
});
