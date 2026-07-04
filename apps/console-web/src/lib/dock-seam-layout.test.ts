import { describe, expect, it } from 'vitest';

import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import { buildDockSeamLayout } from './dock-seam-layout';

const briefing = exampleBriefing as unknown as OperatorBriefing;

describe('dock seam layout', () => {
  it('orders briefing first in operator mode', () => {
    const layout = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing,
      approvalsSummary: '1 pending approval',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'run_contract_baseline · awaiting_approval',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    expect(layout[0]?.id).toBe('briefing');
    expect(layout.map((seam) => seam.id)).toEqual([
      'briefing',
      'approvals',
      'signals',
      'run',
      'thread',
      'command',
    ]);
  });

  it('collapses duplicate seams in operator mode when briefing covers them', () => {
    const layout = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing,
      approvalsSummary: '1 pending approval',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'run_contract_baseline · awaiting_approval',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    expect(layout.find((seam) => seam.id === 'briefing')?.hero).toBe(true);
    expect(layout.find((seam) => seam.id === 'approvals')?.collapsed).toBe(true);
    expect(layout.find((seam) => seam.id === 'signals')?.collapsed).toBe(true);
    expect(layout.find((seam) => seam.id === 'run')?.collapsed).toBe(true);
    expect(layout.find((seam) => seam.id === 'thread')?.collapsed).toBe(true);
  });

  it('allows manual expansion of collapsed seams', () => {
    const layout = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing,
      approvalsSummary: '1 pending approval',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'run_contract_baseline · awaiting_approval',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(['approvals']),
    });

    expect(layout.find((seam) => seam.id === 'approvals')?.collapsed).toBe(false);
  });

  it('uses operator-facing seam titles', () => {
    const layout = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing: null,
      approvalsSummary: '0 pending approvals',
      signalsSummary: 'No signals',
      runSummary: 'No active run',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    const titles = Object.fromEntries(layout.map((seam) => [seam.id, seam.title]));
    expect(titles).toMatchObject({
      run: 'Active Run',
      approvals: 'Approvals',
      signals: 'Signals',
      thread: 'Conversation',
      command: 'Command',
      briefing: 'KAIRO Briefing',
    });
    expect(Object.values(titles).join(' ')).not.toMatch(/SEAM/i);
  });

  it('keeps IDE mode seams expanded by default', () => {
    const layout = buildDockSeamLayout({
      layoutMode: 'ide',
      briefing,
      approvalsSummary: '1 pending approval',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'run_contract_baseline · awaiting_approval',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    expect(layout.find((seam) => seam.id === 'run')?.hero).toBe(true);
    expect(layout.find((seam) => seam.id === 'approvals')?.collapsed).toBe(false);
    expect(layout.find((seam) => seam.id === 'briefing')?.collapsed).toBe(true);
  });
});
