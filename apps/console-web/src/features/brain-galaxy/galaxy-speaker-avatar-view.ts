import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import type { KairoVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { buildEmployeeAvatar, type EmployeeAvatarModel } from '../workspace-agents/employee-avatar';
import { buildEmployeeFaceAvatarUrl } from '../workspace-agents/employee-face-avatar';
import { resolveVaxonAvatarUrl } from '../../lib/vaxon-avatar-view';

export type GalaxySpeakerAvatarView = {
  id: string;
  name: string;
  roleLabel: string;
  kind: 'vaxon' | 'employee';
  initials: string;
  background: string;
  foreground: string;
  faceUrl: string;
  speaking: boolean;
  /** Workspace label when speaker is from another workspace. */
  workspaceLabel: string | null;
  /** Live activity / status line under the avatar. */
  activityLine: string | null;
};

const VAXON_AVATAR: Pick<EmployeeAvatarModel, 'initials' | 'background' | 'foreground'> = {
  initials: 'VX',
  background: '#123a5c',
  foreground: '#d7f6ff',
};

export type ResolveGalaxySpeakerAvatarOptions = {
  speaking?: boolean;
  activityLine?: string | null;
  workspaceLabelById?: Record<string, string>;
  currentWorkspaceId?: string | null;
};

export function resolveGalaxySpeakerAvatar(
  speaker: KairoVoiceSpeaker | null,
  employees: CompanyEmployeeRecord[] = [],
  speakingOrOptions: boolean | ResolveGalaxySpeakerAvatarOptions = false,
): GalaxySpeakerAvatarView | null {
  if (!speaker) {
    return null;
  }

  const options: ResolveGalaxySpeakerAvatarOptions =
    typeof speakingOrOptions === 'boolean'
      ? { speaking: speakingOrOptions }
      : speakingOrOptions;
  const speaking = options.speaking === true;
  const activityLine = options.activityLine?.trim() || null;

  if (speaker.kind === 'vaxon') {
    return {
      id: speaker.id,
      name: speaker.name,
      roleLabel: speaker.roleLabel?.trim() || 'Operator console',
      kind: 'vaxon',
      initials: VAXON_AVATAR.initials,
      background: VAXON_AVATAR.background,
      foreground: VAXON_AVATAR.foreground,
      faceUrl: resolveVaxonAvatarUrl(),
      speaking,
      workspaceLabel: null,
      activityLine,
    };
  }

  const match =
    employees.find((row) => row.employee_id === speaker.id) ??
    employees.find(
      (row) =>
        speaker.azureVoiceId &&
        row.azure_voice_id?.trim() === speaker.azureVoiceId.trim(),
    ) ??
    null;

  if (match) {
    const avatar = buildEmployeeAvatar(match);
    const otherWorkspace =
      options.currentWorkspaceId &&
      match.workspace_id &&
      match.workspace_id !== options.currentWorkspaceId
        ? options.workspaceLabelById?.[match.workspace_id] ?? match.workspace_id
        : null;
    return {
      id: match.employee_id,
      name: match.name,
      roleLabel: match.role_label?.trim() || match.role || 'Agent',
      kind: 'employee',
      initials: avatar.initials,
      background: avatar.background,
      foreground: avatar.foreground,
      faceUrl: avatar.faceUrl,
      speaking,
      workspaceLabel: otherWorkspace,
      activityLine:
        activityLine ||
        (match.status && match.status !== 'idle' ? String(match.status).replace(/_/g, ' ') : null),
    };
  }

  const seed = `${speaker.id}:${speaker.name}`;
  return {
    id: speaker.id,
    name: speaker.name,
    roleLabel: speaker.roleLabel?.trim() || 'Agent',
    kind: 'employee',
    initials: speaker.name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('') || 'AG',
    background: '#2f3d4d',
    foreground: '#d0e0f0',
    faceUrl: buildEmployeeFaceAvatarUrl(seed),
    speaking,
    workspaceLabel: null,
    activityLine,
  };
}
