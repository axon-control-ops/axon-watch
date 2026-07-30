import { describe, expect, it, vi } from 'vitest';

import {
  adviseAttendCtaLabel,
  applyAdviseAttendAction,
  consumeAdviseAttendReply,
  parseAdviseUiAction,
  shouldApplyAdviseAttendOnAffirm,
} from './kairo-sidebar-attend';

describe('kairo-sidebar-attend', () => {
  it('parses Advise Attend actions and labels them', () => {
    const action = parseAdviseUiAction({
      type: 'switch_workspace',
      workspace_id: 'workspace_axon_watch',
      layout_mode: 'operator',
      focus_attention: true,
      cta_label: 'Switch to Axon Watch & open Attention',
    });
    expect(adviseAttendCtaLabel(action)).toBe('Switch to Axon Watch & open Attention');
  });

  it('applies Attend only on affirmative replies when ui_action exists', () => {
    const action = parseAdviseUiAction({
      type: 'switch_workspace',
      workspace_id: 'workspace_axon_watch',
      focus_attention: true,
    });
    expect(
      shouldApplyAdviseAttendOnAffirm({ message: 'yes', adviseUiAction: action }),
    ).toBe(true);
    expect(
      shouldApplyAdviseAttendOnAffirm({ message: 'tell me more', adviseUiAction: action }),
    ).toBe(false);
    expect(
      shouldApplyAdviseAttendOnAffirm({ message: 'yes', adviseUiAction: null }),
    ).toBe(false);
  });

  it('routes Attend through switch + Attention', () => {
    const setCurrentWorkspace = vi.fn();
    const openWorkspaceFile = vi.fn().mockResolvedValue(undefined);
    const setLayoutMode = vi.fn();
    const focusAttentionSidebar = vi.fn();
    applyAdviseAttendAction(
      { setCurrentWorkspace, openWorkspaceFile, setLayoutMode, focusAttentionSidebar },
      {
        type: 'switch_workspace',
        workspace_id: 'workspace_axon_watch',
        layout_mode: 'operator',
        focus_attention: true,
      },
    );
    expect(setCurrentWorkspace).toHaveBeenCalledWith('workspace_axon_watch');
    expect(setLayoutMode).toHaveBeenCalledWith('operator');
    expect(focusAttentionSidebar).toHaveBeenCalledWith(null);
  });

  it('consumes an affirmative Attend reply after executing its action', () => {
    const setCurrentWorkspace = vi.fn();
    const openWorkspaceFile = vi.fn().mockResolvedValue(undefined);
    const focusAttentionSidebar = vi.fn();
    const action = parseAdviseUiAction({
      type: 'switch_workspace',
      workspace_id: 'workspace_dashpro',
      focus_attention: true,
    });

    expect(
      consumeAdviseAttendReply(
        { setCurrentWorkspace, openWorkspaceFile, focusAttentionSidebar },
        { message: 'do it', adviseUiAction: action },
      ),
    ).toBe(true);
    expect(setCurrentWorkspace).toHaveBeenCalledWith('workspace_dashpro');
    expect(focusAttentionSidebar).toHaveBeenCalledWith(null);
  });
});
