import { describe, expect, it } from 'vitest';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import { employeeVoiceSpeaker, vaxonVoiceSpeaker } from '../../lib/kairo-voice-utterance';
import { resolveGalaxySpeakerAvatar } from './galaxy-speaker-avatar-view';

const employee: CompanyEmployeeRecord = {
  employee_id: 'emp_sentry',
  workspace_id: 'ws_demo',
  name: 'Sentry Watcher',
  role: 'watcher',
  role_label: 'Watcher',
  schedule: 'always_on',
  schedule_label: 'Always on',
  status: 'idle',
  enabled: true,
  primary: false,
  owns: 'sentry watch',
  azure_voice_id: 'en-GB-SoniaNeural',
};

describe('resolveGalaxySpeakerAvatar', () => {
  it('builds the VAXON operator face avatar', () => {
    const view = resolveGalaxySpeakerAvatar(vaxonVoiceSpeaker(), [], true);
    expect(view?.kind).toBe('vaxon');
    expect(view?.initials).toBe('VX');
    expect(view?.speaking).toBe(true);
    expect(view?.faceUrl.startsWith('data:image/svg+xml')).toBe(true);
  });

  it('resolves employee face avatars from roster identity', () => {
    const view = resolveGalaxySpeakerAvatar(employeeVoiceSpeaker(employee), [employee]);
    expect(view?.kind).toBe('employee');
    expect(view?.name).toBe('Sentry Watcher');
    expect(view?.initials).toBe('SW');
    expect(view?.roleLabel).toBe('Watcher');
    expect(view?.faceUrl.startsWith('data:image/svg+xml')).toBe(true);
  });

  it('labels speakers from another workspace', () => {
    const view = resolveGalaxySpeakerAvatar(employeeVoiceSpeaker(employee), [employee], {
      currentWorkspaceId: 'ws_other',
      workspaceLabelById: { ws_demo: 'DashPro' },
    });
    expect(view?.workspaceLabel).toBe('DashPro');
  });

  it('returns null without an active speaker', () => {
    expect(resolveGalaxySpeakerAvatar(null)).toBeNull();
  });
});
