export type ComposerRuntimePrefs = {
  runtime_target?: string;
  cursor_cli_model?: string;
  codex_cli_model?: string;
  claude_cli_model?: string;
};

type ComposerRuntimePrefsMap = {
  workspaces: Record<string, ComposerRuntimePrefs>;
  updatedAt: string;
};

const STORAGE_KEY = 'axon-watch.composerRuntimePrefs';

function readMap(): ComposerRuntimePrefsMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { workspaces: {}, updatedAt: '' };
    }
    const parsed = JSON.parse(raw) as ComposerRuntimePrefsMap;
    return {
      workspaces:
        parsed?.workspaces && typeof parsed.workspaces === 'object' ? parsed.workspaces : {},
      updatedAt: typeof parsed?.updatedAt === 'string' ? parsed.updatedAt : '',
    };
  } catch {
    return { workspaces: {}, updatedAt: '' };
  }
}

function writeMap(map: ComposerRuntimePrefsMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore quota or privacy-mode failures.
  }
}

export function readComposerRuntimePrefs(workspaceId: string | null): ComposerRuntimePrefs {
  if (!workspaceId) {
    return {};
  }
  return readMap().workspaces[workspaceId] ?? {};
}

export function writeComposerRuntimePrefs(
  workspaceId: string,
  patch: ComposerRuntimePrefs,
): ComposerRuntimePrefs {
  const map = readMap();
  const current = map.workspaces[workspaceId] ?? {};
  const next = { ...current, ...patch };
  map.workspaces[workspaceId] = next;
  map.updatedAt = new Date().toISOString();
  writeMap(map);
  return next;
}
