import {
  canonicalWorkspaceLabel,
  normalizeVoiceTranscript,
  resolveWorkspaceIdFromPhrase,
} from '../../lib/kairo-entity-labels';

export type ConversationNavigationIntent = {
  kind:
    | 'focus_workspace'
    | 'enter_workspace'
    | 'focus_attention'
    | 'focus_briefing'
    | 'switch_center_view';
  workspaceId?: string;
  centerView?: 'graph' | 'grid';
  reply: string;
};

export type WorkspaceNavTarget = {
  workspace_id: string;
  display_name: string;
};

const ATTENTION_RE = /\b(open|show|focus)\s+attention\b/i;
const BRIEFING_NAV_RE =
  /\b(?:open|show|focus|pull up)\s+(?:me\s+)?(?:the\s+)?(?:(?:vaxon|kairo|operator)\s+)?briefing\b|\bbriefing\s+(?:view|panel|tab)\b/i;
/** Explicit view switches only — bare "fleet" in "fleet health" must not match. */
const GRID_NAV_RE =
  /\b(?:show|open|switch to|go to|return to)\s+(?:the\s+)?(?:fleet\s+)?grid(?:\s+(?:view|mode))?\b|\bgrid\s+(?:view|mode)\b|\bfleet\s+(?:grid|view|mode)\b/i;
const BRAIN_NAV_RE =
  /\b(?:show|open|switch to|go to|return to)\s+(?:the\s+)?(?:brain(?:\s+galaxy)?|galaxy(?:\s+view)?)\b|\b(?:brain|galaxy)\s+(?:view|mode)\b/i;
const FEED_NAV_RE =
  /\b(?:show|open|switch to|go to)\s+(?:the\s+)?(?:incident\s+)?feed(?:\s+(?:view|mode))?\b|\b(?:incident|feed)\s+(?:view|mode)\b/i;
/** Enter the coding surface — "open DashPro workspace", "go into DashPro". */
const ENTER_WORKSPACE_RE =
  /\b(?:open|enter|go into|launch)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+workspace)?\s*$/i;
/** Focus without leaving Mission Control — "show me DashPro", "focus DashPro". */
const FOCUS_WORKSPACE_RE =
  /\b(?:show|focus|switch to)\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+workspace)?\s*$/i;

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

export function workspaceGalaxyNodeId(workspaceId: string): string {
  return `ws_${workspaceId.trim()}`;
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
  if (BRIEFING_NAV_RE.test(trimmed)) {
    return {
      kind: 'focus_briefing',
      reply: 'Opening the briefing for you.',
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

  const enterMatch = trimmed.match(ENTER_WORKSPACE_RE);
  if (enterMatch?.[1]) {
    const workspace = matchWorkspace(enterMatch[1], workspaces);
    if (workspace) {
      const label = canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name);
      return {
        kind: 'enter_workspace',
        workspaceId: workspace.workspace_id,
        reply: `Opening ${label}.`,
      };
    }
  }

  const focusMatch = trimmed.match(FOCUS_WORKSPACE_RE);
  if (focusMatch?.[1]) {
    const workspace = matchWorkspace(focusMatch[1], workspaces);
    if (workspace) {
      const label = canonicalWorkspaceLabel(workspace.workspace_id, workspace.display_name);
      return {
        kind: 'focus_workspace',
        workspaceId: workspace.workspace_id,
        reply: `${label} is on deck.`,
      };
    }
  }

  return null;
}
