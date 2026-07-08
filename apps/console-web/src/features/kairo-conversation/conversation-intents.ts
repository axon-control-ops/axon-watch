import {
  canonicalWorkspaceLabel,
  normalizeVoiceTranscript,
  resolveWorkspaceIdFromPhrase,
} from '../../lib/kairo-entity-labels';

export type ConversationNavigationIntent = {
  kind: 'focus_workspace' | 'focus_attention' | 'switch_center_view';
  workspaceId?: string;
  centerView?: 'graph' | 'grid';
  reply: string;
};

export type WorkspaceNavTarget = {
  workspace_id: string;
  display_name: string;
};

const ATTENTION_RE = /\b(open|show|focus)\s+attention\b/i;
/** Explicit view switches only — bare "fleet" in "fleet health" must not match. */
const GRID_NAV_RE =
  /\b(?:show|open|switch to|go to|return to)\s+(?:the\s+)?(?:fleet\s+)?grid(?:\s+(?:view|mode))?\b|\bgrid\s+(?:view|mode)\b|\bfleet\s+(?:grid|view|mode)\b/i;
const BRAIN_NAV_RE =
  /\b(?:show|open|switch to|go to|return to)\s+(?:the\s+)?(?:brain(?:\s+galaxy)?|galaxy(?:\s+view)?)\b|\b(?:brain|galaxy)\s+(?:view|mode)\b/i;
const FEED_NAV_RE =
  /\b(?:show|open|switch to|go to)\s+(?:the\s+)?(?:incident\s+)?feed(?:\s+(?:view|mode))?\b|\b(?:incident|feed)\s+(?:view|mode)\b/i;
const SHOW_WORKSPACE_RE =
  /\b(?:show|focus|open|switch to)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+workspace)?\s*$/i;

function normalizeLabel(value: string): string {
  return normalizeVoiceTranscript(value).trim().toLowerCase().replace(/\s+/g, ' ');
}

function matchWorkspace(
  phrase: string,
  workspaces: WorkspaceNavTarget[],
): WorkspaceNavTarget | null {
  const aliasWorkspaceId = resolveWorkspaceIdFromPhrase(phrase);
  if (aliasWorkspaceId) {
    const aliasMatch = workspaces.find((workspace) => workspace.workspace_id === aliasWorkspaceId);
    if (aliasMatch) {
      return aliasMatch;
    }
  }

  const needle = normalizeLabel(phrase);
  if (!needle) {
    return null;
  }
  const exact = workspaces.find(
    (workspace) =>
      normalizeLabel(workspace.display_name) === needle ||
      normalizeLabel(workspace.workspace_id) === needle ||
      normalizeLabel(canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name)) ===
        needle,
  );
  if (exact) {
    return exact;
  }
  return (
    workspaces.find((workspace) => normalizeLabel(workspace.display_name).includes(needle)) ??
    workspaces.find((workspace) =>
      normalizeLabel(canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name)).includes(
        needle,
      ),
    ) ??
    workspaces.find((workspace) => normalizeLabel(workspace.workspace_id).includes(needle)) ??
    null
  );
}

export function resolveConversationNavigationIntent(
  content: string,
  workspaces: WorkspaceNavTarget[],
): ConversationNavigationIntent | null {
  const trimmed = normalizeVoiceTranscript(content.trim());
  if (!trimmed) {
    return null;
  }

  if (ATTENTION_RE.test(trimmed)) {
    return {
      kind: 'focus_attention',
      reply: 'Opening Attention for you.',
    };
  }
  if (GRID_NAV_RE.test(trimmed)) {
    return {
      kind: 'switch_center_view',
      centerView: 'grid',
      reply: 'Switching to fleet grid view.',
    };
  }
  if (BRAIN_NAV_RE.test(trimmed)) {
    return {
      kind: 'switch_center_view',
      centerView: 'graph',
      reply: 'Returning to brain galaxy view.',
    };
  }
  if (FEED_NAV_RE.test(trimmed)) {
    return {
      kind: 'switch_center_view',
      centerView: 'grid',
      reply: 'Opening fleet grid — check the dock for incident detail.',
    };
  }

  const workspaceMatch = trimmed.match(SHOW_WORKSPACE_RE);
  if (workspaceMatch?.[1]) {
    const workspace = matchWorkspace(workspaceMatch[1], workspaces);
    if (workspace) {
      const label = canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name);
      return {
        kind: 'focus_workspace',
        workspaceId: workspace.workspace_id,
        reply: `Focusing ${label}.`,
      };
    }
  }

  return null;
}
