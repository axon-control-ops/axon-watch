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
    setDockHeroMode: vi.fn(),
    restoreComposerDraft: vi.fn(),
    setLayoutMode,
    setCurrentWorkspace: vi.fn(),
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

describe('focusAttentionSidebar', () => {
  it('opens the IDE attention panel without switching layout', () => {
    const ideAttentionPanelOpen = ref(false);
    const setCurrentWorkspace = vi.fn();
    const layoutMode = ref<'ide' | 'operator'>('ide');
    const operatorCenterView = ref<'grid' | 'graph'>('graph');
    const slice = createOperatorFocusSlice({
      layoutMode,
      operatorBriefing: ref(null),
      highlightedSignalId: ref(null),
      ideAttentionPanelOpen,
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
      setDockHeroMode: vi.fn(),
      restoreComposerDraft: vi.fn(),
      setLayoutMode: vi.fn(),
      setCurrentWorkspace,
    } as Parameters<typeof createOperatorFocusSlice>[0]);

    slice.focusAttentionSidebar('signal_x');

    expect(ideAttentionPanelOpen.value).toBe(true);
    expect(operatorCenterView.value).toBe('graph');
    expect(setCurrentWorkspace).not.toHaveBeenCalled();
  });

  it('switches Mission Control to grid and selects the signal workspace', () => {
    const setCurrentWorkspace = vi.fn();
    const operatorCenterView = ref<'grid' | 'graph'>('graph');
    const highlightedSignalId = ref<string | null>(null);
    const slice = createOperatorFocusSlice({
      layoutMode: ref('operator'),
      operatorBriefing: ref({
        top_signals: [
          {
            signal_id: 'signal_dash',
            workspace_id: 'workspace_dashpro',
            title: 'Dash alert',
          },
        ],
      }),
      highlightedSignalId,
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
      setDockHeroMode: vi.fn(),
      restoreComposerDraft: vi.fn(),
      setLayoutMode: vi.fn(),
      setCurrentWorkspace,
    } as unknown as Parameters<typeof createOperatorFocusSlice>[0]);

    slice.focusAttentionSidebar('signal_dash');

    expect(operatorCenterView.value).toBe('grid');
    expect(highlightedSignalId.value).toBe('signal_dash');
    expect(setCurrentWorkspace).toHaveBeenCalledWith('workspace_dashpro');
  });

  it('opens the spoken alert details when Open Attention omits an id', () => {
    const highlightedSignalId = ref<string | null>(null);
    const setCurrentWorkspace = vi.fn();
    const slice = createOperatorFocusSlice({
      layoutMode: ref('operator'),
      operatorBriefing: ref({
        top_signals: [],
        operator_presence: {
          spoken_alert: { signal_id: 'signal_dash' },
        },
      }),
      attentionSignals: ref([
        {
          signal_id: 'signal_other',
          workspace_id: 'workspace_other',
          title: 'Other warning',
          severity: 'warning',
        },
        {
          signal_id: 'signal_dash',
          workspace_id: 'workspace_dashpro',
          title: 'DashPro CI failed',
          severity: 'critical',
        },
      ]),
      highlightedSignalId,
      ideAttentionPanelOpen: ref(false),
      ideBriefingPanelOpen: ref(false),
      ideExplorerCollapsed: ref(false),
      signalsSeamEmphasized: ref(false),
      missionControlEmphasized: ref(false),
      connectorsEmphasized: ref(false),
      briefingSeamEmphasized: ref(false),
      operatorCenterView: ref('graph'),
      dockHeroMode: ref('command'),
      expandedDockSeams: ref(new Set()),
      dockThreadSeamTouched: ref(false),
      setDockHeroMode: vi.fn(),
      restoreComposerDraft: vi.fn(),
      setLayoutMode: vi.fn(),
      setCurrentWorkspace,
    } as unknown as Parameters<typeof createOperatorFocusSlice>[0]);

    slice.focusAttentionSidebar();

    expect(highlightedSignalId.value).toBe('signal_dash');
    expect(setCurrentWorkspace).toHaveBeenCalledWith('workspace_dashpro');
  });
});

describe('focusLiveOperations', () => {
  it('expands the LIVE OPERATIONS thread seam instead of collapsing it', () => {
    const expandedDockSeams = ref(new Set<string>());
    const operatorCenterView = ref<'grid' | 'graph'>('graph');
    const layoutMode = ref<'ide' | 'operator'>('ide');
    const setLayoutMode = vi.fn((mode: 'ide' | 'operator') => {
      layoutMode.value = mode;
    });
    const setDockHeroMode = vi.fn();
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
      expandedDockSeams,
      dockThreadSeamTouched: ref(false),
      setDockHeroMode,
      restoreComposerDraft: vi.fn(),
      setLayoutMode,
      setCurrentWorkspace: vi.fn(),
    } as unknown as Parameters<typeof createOperatorFocusSlice>[0]);

    slice.focusLiveOperations();

    expect(setLayoutMode).toHaveBeenCalledWith('operator');
    // Brain Galaxy hides the live-ops dock, so the grid view must win.
    expect(operatorCenterView.value).toBe('grid');
    expect(expandedDockSeams.value.has('thread')).toBe(true);
    expect(setDockHeroMode).not.toHaveBeenCalled();
  });
});
