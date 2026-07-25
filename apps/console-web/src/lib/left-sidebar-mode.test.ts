import { describe, expect, it } from 'vitest';

import type { OperatorBriefing } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import {
  leftSidebarAttentionBadgeCount,
  resolveDefaultLeftSidebarMode,
} from './left-sidebar-mode';

const briefing = exampleBriefing as unknown as OperatorBriefing;

describe('left sidebar mode', () => {
  it('defaults to attention when approvals are pending', () => {
    expect(
      resolveDefaultLeftSidebarMode({
        pendingApprovals: 2,
        briefing,
      }),
    ).toBe('attention');
  });

  it('defaults to attention for interruptive signals', () => {
    expect(
      resolveDefaultLeftSidebarMode({
        pendingApprovals: 0,
        briefing: {
          ...briefing,
          top_signals: [
            {
              ...briefing.top_signals[0]!,
              severity: 'high',
            },
          ],
        } as OperatorBriefing,
      }),
    ).toBe('attention');
  });

  it('defaults to workspaces when no attention pressure exists', () => {
    expect(
      resolveDefaultLeftSidebarMode({
        pendingApprovals: 0,
        briefing: {
          ...briefing,
          pending_approvals: { count: 0, items: [] },
          top_signals: [],
        } as OperatorBriefing,
      }),
    ).toBe('workspaces');
  });

  it('counts attention badge from approvals, high signals, and awaiting engagement', () => {
    expect(
      leftSidebarAttentionBadgeCount({
        pendingApprovals: 1,
        briefing: {
          ...briefing,
          top_signals: [
            {
              ...briefing.top_signals[0]!,
              severity: 'high',
            },
            {
              ...briefing.top_signals[0]!,
              signal_id: 'signal_info',
              severity: 'info',
            },
          ],
        } as OperatorBriefing,
      }),
    ).toBe(2);

    expect(
      leftSidebarAttentionBadgeCount({
        pendingApprovals: 0,
        briefing: {
          ...briefing,
          top_signals: [],
          awaiting_engagement_count: 2,
        } as OperatorBriefing,
      }),
    ).toBe(2);
  });
});
