import { describe, expect, it } from 'vitest';

import type { OperatorBriefing, RunRecord, RuntimeSummary } from '../contracts/canonical';
import exampleBriefing from '../../../../packages/shared-types/fixtures/operator-briefing.example.json';
import {
  briefingHasInterruptiveSignals,
  buildDockSeamLayout,
} from './dock-seam-layout';

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

  it('collapses signals in operator mode only for interruptive severities', () => {
    const interruptiveBriefing = {
      ...briefing,
      top_signals: [
        {
          ...briefing.top_signals[0]!,
          severity: 'high',
        },
      ],
    } as OperatorBriefing;

    const collapsed = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing: interruptiveBriefing,
      approvalsSummary: '0 pending approvals',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'No active run',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    expect(briefingHasInterruptiveSignals(interruptiveBriefing)).toBe(true);
    expect(collapsed.find((seam) => seam.id === 'signals')?.collapsed).toBe(true);

    const expanded = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing: interruptiveBriefing,
      approvalsSummary: '0 pending approvals',
      signalsSummary: 'Watch summary degraded',
      runSummary: 'No active run',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(['signals']),
    });

    expect(expanded.find((seam) => seam.id === 'signals')?.collapsed).toBe(false);
  });

  it('keeps non-interruptive signals expanded in operator mode', () => {
    const ambientBriefing = {
      ...briefing,
      top_signals: [
        {
          ...briefing.top_signals[0]!,
          severity: 'warning',
        },
      ],
    } as OperatorBriefing;

    const layout = buildDockSeamLayout({
      layoutMode: 'operator',
      briefing: ambientBriefing,
      approvalsSummary: '0 pending approvals',
      signalsSummary: 'Ambient watch note',
      runSummary: 'No active run',
      threadSummary: 'No active conversation',
      expandedSeams: new Set(),
    });

    expect(briefingHasInterruptiveSignals(ambientBriefing)).toBe(false);
    expect(layout.find((seam) => seam.id === 'signals')?.collapsed).toBe(false);
  });
});
