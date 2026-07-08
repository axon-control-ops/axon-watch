import { describe, expect, it } from 'vitest';

import {
  canonicalBrainGraphLabel,
  canonicalWorkspaceLabel,
  normalizeBrainGraphSnapshot,
  normalizeKairoCopy,
  normalizeVoiceTranscript,
  resolveWorkspaceIdFromPhrase,
} from './kairo-entity-labels';

describe('kairo entity labels', () => {
  it('normalizes vixen mishear in voice transcripts', () => {
    expect(normalizeVoiceTranscript('hey vixen what is dash pro doing')).toBe(
      'hey VAXON what is DashPro doing',
    );
    expect(normalizeVoiceTranscript('open desk pro workspace')).toBe('open DashPro workspace');
  });

  it('normalizes display copy', () => {
    expect(normalizeKairoCopy("Dash Pro's sitting idle")).toBe("DashPro's sitting idle");
  });

  it('returns canonical workspace labels', () => {
    expect(canonicalWorkspaceLabel('workspace_axon_watch', 'axon-watch')).toBe('Axon Watch');
    expect(canonicalWorkspaceLabel('workspace_dashpro', 'dashpro')).toBe('DashPro');
  });

  it('resolves workspace aliases from spoken phrases', () => {
    expect(resolveWorkspaceIdFromPhrase('desk pro')).toBe('workspace_dashpro');
    expect(resolveWorkspaceIdFromPhrase('axon-watch')).toBe('workspace_axon_watch');
  });

  it('normalizes brain graph workspace labels', () => {
    const snapshot = normalizeBrainGraphSnapshot({
      generated_at: 'now',
      watch_connected: true,
      node_count: 2,
      edge_count: 0,
      edges: [],
      nodes: [
        {
          node_id: 'core',
          kind: 'core',
          label: 'kairo',
          tone: 'nominal',
          workspace_id: null,
          detail: '',
        },
        {
          node_id: 'ws1',
          kind: 'workspace',
          label: 'DASHPRO',
          tone: 'nominal',
          workspace_id: 'workspace_dashpro',
          detail: '',
        },
      ],
    });
    expect(snapshot.nodes[0]?.label).toBe('VAXON');
    expect(snapshot.nodes[1]?.label).toBe('DashPro');
    expect(canonicalBrainGraphLabel('cairo', 'core')).toBe('VAXON');
  });
});
