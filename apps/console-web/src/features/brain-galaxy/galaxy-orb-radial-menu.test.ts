import { describe, expect, it, vi } from 'vitest';

import {
  dispatchOrbRadialMenuAction,
  ORB_RADIAL_MENU_ITEMS,
  orbRadialMenuItemPosition,
  type OrbRadialMenuShell,
} from './galaxy-orb-radial-menu';

describe('galaxy-orb-radial-menu', () => {
  it('lays out five command ring segments', () => {
    expect(ORB_RADIAL_MENU_ITEMS).toHaveLength(5);
    expect(ORB_RADIAL_MENU_ITEMS.map((item) => item.id)).toEqual([
      'talk',
      'team',
      'skills',
      'signals',
      'settings',
    ]);
  });

  it('positions items on a circle', () => {
    const top = orbRadialMenuItemPosition(-90, 100);
    expect(top.x).toBeCloseTo(0, 1);
    expect(top.y).toBeCloseTo(-100, 1);
  });

  it('routes team to the roster and talk to the voice handler', () => {
    const onTalk = vi.fn();
    const shell = {
      layoutMode: 'operator',
      setLayoutMode: vi.fn(),
      revealTeamRosterForActiveEmployee: vi.fn(),
      focusAttentionSidebar: vi.fn(),
    } as {
      layoutMode: string;
      setLayoutMode: ReturnType<typeof vi.fn>;
      revealTeamRosterForActiveEmployee: ReturnType<typeof vi.fn>;
      focusAttentionSidebar: ReturnType<typeof vi.fn>;
    };

    dispatchOrbRadialMenuAction('talk', shell as unknown as OrbRadialMenuShell, onTalk);
    dispatchOrbRadialMenuAction('team', shell as unknown as OrbRadialMenuShell, onTalk);

    expect(onTalk).toHaveBeenCalledOnce();
    expect(shell.setLayoutMode).toHaveBeenCalledWith('ide');
    expect(shell.revealTeamRosterForActiveEmployee).toHaveBeenCalledOnce();
  });
});
