import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';

import { createOperatorFocusSlice } from './create-operator-focus-slice';

function createSlice(initialLayout: 'ide' | 'operator' = 'ide') {
  const layoutMode = ref<'ide' | 'operator'>(initialLayout);
  const operatorCenterView = ref<'grid' | 'graph'>('graph');
  const setLayoutMode = vi.fn((mode: 'ide' | 'operator') => {
    layoutMode.value = mode;
  });
  const slice = createOperatorFocusSlice({
    layoutMode,
    operatorBriefing: ref(null),
    highlightedSignalId: ref(null),
    ideAttentionPanelOpen: ref(false),
    ideBriefingPanelOpen: ref(false),
    ideExplorerCollapsed: ref(false),
    signalsSeamEmphasized: ref(false),
    missionControlEmphasized: ref(false),
    connectorsEmphasized: ref(false),
    briefingSeamEmphasized: ref(false),
    operatorCenterView,
    dockHeroMode: ref('command'),
    expandedDockSeams: ref(new Set()),
    dockThreadSeamTouched: ref(false),
    setLeftSidebarMode: vi.fn(),
    setDockHeroMode: vi.fn(),
    restoreComposerDraft: vi.fn(),
    setLayoutMode,
  } as Parameters<typeof createOperatorFocusSlice>[0]);
  return { layoutMode, operatorCenterView, setLayoutMode, slice };
}

describe('afterRunLifecycleMutation', () => {
  it('keeps IDE Continue on its current surface when preserveSurface is set', () => {
    const { layoutMode, operatorCenterView, setLayoutMode, slice } = createSlice('ide');

    slice.afterRunLifecycleMutation({ preserveSurface: true });

    expect(setLayoutMode).not.toHaveBeenCalled();
    expect(layoutMode.value).toBe('ide');
    expect(operatorCenterView.value).toBe('graph');
  });

  it('never yanks IDE to Mission Control for lifecycle mutations', () => {
    const { layoutMode, operatorCenterView, setLayoutMode, slice } = createSlice('ide');

    slice.afterRunLifecycleMutation();

    expect(setLayoutMode).not.toHaveBeenCalled();
    expect(layoutMode.value).toBe('ide');
    expect(operatorCenterView.value).toBe('graph');
  });

  it('still focuses Mission Control for operator lifecycle actions', () => {
    const { layoutMode, operatorCenterView, setLayoutMode, slice } = createSlice('operator');

    slice.afterRunLifecycleMutation();

    expect(setLayoutMode).not.toHaveBeenCalled();
    expect(layoutMode.value).toBe('operator');
    expect(operatorCenterView.value).toBe('grid');
  });
});
