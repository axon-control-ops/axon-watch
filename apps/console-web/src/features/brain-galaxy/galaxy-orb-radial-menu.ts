import { navigateToAppSurface } from '../../lib/app-surface-route';
import { navigateToSettingsSection } from '../../lib/settings-section-route';

export type OrbRadialMenuAction = 'talk' | 'team' | 'skills' | 'signals' | 'settings';

export type OrbRadialMenuItem = {
  id: OrbRadialMenuAction;
  label: string;
  detail: string;
  shortLabel: string;
  angleDeg: number;
};

export const ORB_RADIAL_MENU_ITEMS: OrbRadialMenuItem[] = [
  {
    id: 'talk',
    label: 'Talk',
    detail: 'Toggle hands-free voice',
    shortLabel: 'VOX',
    angleDeg: -90,
  },
  {
    id: 'team',
    label: 'Team',
    detail: 'Open company roster',
    shortLabel: 'TEAM',
    angleDeg: -18,
  },
  {
    id: 'skills',
    label: 'Skills',
    detail: 'Browse playbooks',
    shortLabel: 'SKL',
    angleDeg: 54,
  },
  {
    id: 'signals',
    label: 'Signals',
    detail: 'Attention inbox',
    shortLabel: 'SIG',
    angleDeg: 126,
  },
  {
    id: 'settings',
    label: 'Settings',
    detail: 'Voice and agents',
    shortLabel: 'SET',
    angleDeg: 198,
  },
];

export function orbRadialMenuItemPosition(
  angleDeg: number,
  radiusPx: number,
): { x: number; y: number } {
  const radians = (angleDeg * Math.PI) / 180;
  return {
    x: Math.cos(radians) * radiusPx,
    y: Math.sin(radians) * radiusPx,
  };
}

import type { LayoutMode } from '../../stores/shell';

export type OrbRadialMenuShell = {
  layoutMode: LayoutMode | string;
  setLayoutMode: (mode: LayoutMode) => void;
  revealTeamRosterForActiveEmployee: () => void;
  focusAttentionSidebar: () => void;
};

export function dispatchOrbRadialMenuAction(
  action: OrbRadialMenuAction,
  shell: OrbRadialMenuShell,
  onTalk: () => void | Promise<void>,
): void {
  switch (action) {
    case 'talk':
      void onTalk();
      return;
    case 'team':
      if (shell.layoutMode !== 'ide') {
        shell.setLayoutMode('ide');
      }
      shell.revealTeamRosterForActiveEmployee();
      return;
    case 'skills':
      navigateToAppSurface('skills');
      return;
    case 'signals':
      shell.focusAttentionSidebar();
      return;
    case 'settings':
      navigateToSettingsSection('voice');
      return;
    default:
      return;
  }
}
