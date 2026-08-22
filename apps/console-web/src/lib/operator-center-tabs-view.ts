import type { OperatorCenterView } from './operator-brain-graph-view';

export type OperatorCenterTab = {
  id: OperatorCenterView;
  label: string;
  title: string;
  eyebrow: string;
};

export const OPERATOR_CENTER_TABS: readonly OperatorCenterTab[] = [
  {
    id: 'mission',
    label: 'Mission Control',
    title: 'Mission Control',
    eyebrow: 'Operator center',
  },
  {
    id: 'attention',
    label: 'Attention',
    title: 'Attention',
    eyebrow: 'Operator center',
  },
  {
    id: 'dispatch',
    label: 'Dispatch',
    title: 'Dispatch work',
    eyebrow: 'Operator center',
  },
  {
    id: 'vaxon',
    label: 'VAXON',
    title: 'VAXON',
    eyebrow: 'Executive command',
  },
  {
    id: 'email',
    label: 'Email',
    title: 'Email',
    eyebrow: 'Operator center',
  },
  {
    id: 'graph',
    label: 'Brain Graph',
    title: 'Brain Graph',
    eyebrow: 'Operator center',
  },
] as const;

export function operatorCenterTabMeta(view: OperatorCenterView): OperatorCenterTab {
  return (
    OPERATOR_CENTER_TABS.find((tab) => tab.id === view) ??
    OPERATOR_CENTER_TABS[0]
  );
}

export function operatorCenterTabBadgeCount(input: {
  view: OperatorCenterView;
  attentionCount: number;
  dispatchQueuedCount?: number;
  openEmailCount?: number;
}): number | null {
  if (input.view === 'attention' && input.attentionCount > 0) {
    return input.attentionCount;
  }
  if (input.view === 'dispatch' && (input.dispatchQueuedCount ?? 0) > 0) {
    return input.dispatchQueuedCount ?? 0;
  }
  if (input.view === 'email' && (input.openEmailCount ?? 0) > 0) {
    return input.openEmailCount ?? 0;
  }
  return null;
}
