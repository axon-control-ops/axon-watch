import { readonly, ref, watch } from 'vue';

export type VaxonBriefingInteraction = {
  workspaceId: string;
  line: string;
  createdAt: number;
  utteranceKey: string;
};

const STORAGE_KEY = 'axon-vaxon-briefing-interaction';

const pendingByWorkspace = ref<Record<string, VaxonBriefingInteraction>>({});
const dismissedKeys = ref<Set<string>>(new Set());

/** Reactive map for IDE speech chips / roster docks that must stay until dismissed. */
export const vaxonBriefingPendingByWorkspace = readonly(pendingByWorkspace);

function loadFromStorage(): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw) as {
      pending?: Record<string, VaxonBriefingInteraction>;
      dismissed?: string[];
    };
    pendingByWorkspace.value = parsed.pending ?? {};
    dismissedKeys.value = new Set(parsed.dismissed ?? []);
  } catch {
    pendingByWorkspace.value = {};
    dismissedKeys.value = new Set();
  }
}

function persistToStorage(): void {
  if (typeof sessionStorage === 'undefined') {
    return;
  }
  sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      pending: pendingByWorkspace.value,
      dismissed: [...dismissedKeys.value],
    }),
  );
}

loadFromStorage();

watch([pendingByWorkspace, dismissedKeys], persistToStorage, { deep: true });

export function vaxonBriefingInteractionKey(line: string, speakerId?: string | null): string {
  const id = (speakerId || 'vaxon').trim();
  const text = line.trim().slice(0, 240);
  return `${id}:${text}`;
}

export function recordVaxonBriefingInteraction(input: {
  workspaceId: string;
  line: string;
  utteranceKey?: string;
}): void {
  const workspaceId = input.workspaceId.trim();
  const line = input.line.trim();
  if (!workspaceId || !line) {
    return;
  }
  const utteranceKey =
    input.utteranceKey?.trim() || vaxonBriefingInteractionKey(line, 'vaxon');
  if (dismissedKeys.value.has(utteranceKey)) {
    return;
  }
  pendingByWorkspace.value = {
    ...pendingByWorkspace.value,
    [workspaceId]: {
      workspaceId,
      line,
      createdAt: Date.now(),
      utteranceKey,
    },
  };
}

export function getVaxonBriefingInteraction(
  workspaceId: string,
): VaxonBriefingInteraction | null {
  const id = workspaceId.trim();
  if (!id) {
    return null;
  }
  const row = pendingByWorkspace.value[id];
  if (!row || dismissedKeys.value.has(row.utteranceKey)) {
    return null;
  }
  return row;
}

export function dismissVaxonBriefingInteraction(workspaceId: string): void {
  const id = workspaceId.trim();
  const row = pendingByWorkspace.value[id];
  if (row) {
    dismissedKeys.value = new Set([...dismissedKeys.value, row.utteranceKey]);
  }
  const next = { ...pendingByWorkspace.value };
  delete next[id];
  pendingByWorkspace.value = next;
}

export function clearVaxonBriefingInteraction(workspaceId: string): void {
  const id = workspaceId.trim();
  const next = { ...pendingByWorkspace.value };
  delete next[id];
  pendingByWorkspace.value = next;
}

/** Test-only: wipe in-memory briefing state. */
export function resetVaxonBriefingInteractionForTests(): void {
  pendingByWorkspace.value = {};
  dismissedKeys.value = new Set();
}
