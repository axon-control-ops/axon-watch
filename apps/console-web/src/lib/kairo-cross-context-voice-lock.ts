/**
 * Exclusive cross-tab / cross-window voice floor.
 *
 * Web Locks alone are unreliable across Tauri/webview and multi-process
 * Chromium contexts in this app — use a localStorage lease with heartbeat,
 * plus an in-process mutex for same-realm waiters that share one owner id.
 */

export const KAIRO_CROSS_CONTEXT_VOICE_LOCK_KEY = 'axon-kairo-cross-context-voice-lock';

const LOCK_TTL_MS = 12_000;
const HEARTBEAT_MS = 3_000;
const POLL_MS = 120;
const MAX_WAIT_MS = 90_000;

type VoiceLockLease = {
  ownerId: string;
  expiresAt: number;
  startedAt: number;
};

type LockStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

const ownerId =
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `voice-owner-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const memoryStore = new Map<string, string>();
let inProcessTail: Promise<void> = Promise.resolve();

function createMemoryStorage(): LockStorage {
  return {
    getItem: (key) => memoryStore.get(key) ?? null,
    setItem: (key, value) => {
      memoryStore.set(key, value);
    },
    removeItem: (key) => {
      memoryStore.delete(key);
    },
  };
}

function storage(): LockStorage {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage;
    }
  } catch {
    /* private mode */
  }
  return createMemoryStorage();
}

function readLease(store: LockStorage): VoiceLockLease | null {
  try {
    const raw = store.getItem(KAIRO_CROSS_CONTEXT_VOICE_LOCK_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<VoiceLockLease>;
    if (
      typeof parsed.ownerId !== 'string' ||
      typeof parsed.expiresAt !== 'number' ||
      typeof parsed.startedAt !== 'number'
    ) {
      return null;
    }
    return {
      ownerId: parsed.ownerId,
      expiresAt: parsed.expiresAt,
      startedAt: parsed.startedAt,
    };
  } catch {
    return null;
  }
}

function writeLease(store: LockStorage, lease: VoiceLockLease): void {
  store.setItem(KAIRO_CROSS_CONTEXT_VOICE_LOCK_KEY, JSON.stringify(lease));
}

function clearOwnLease(store: LockStorage): void {
  const current = readLease(store);
  if (current?.ownerId === ownerId) {
    store.removeItem(KAIRO_CROSS_CONTEXT_VOICE_LOCK_KEY);
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, ms);
  });
}

function tryAcquire(store: LockStorage, now: number): boolean {
  const current = readLease(store);
  if (current && current.expiresAt > now && current.ownerId !== ownerId) {
    return false;
  }
  const lease: VoiceLockLease = {
    ownerId,
    startedAt: now,
    expiresAt: now + LOCK_TTL_MS,
  };
  writeLease(store, lease);
  const confirmed = readLease(store);
  return Boolean(confirmed && confirmed.ownerId === ownerId);
}

function refreshLease(store: LockStorage): void {
  const now = Date.now();
  const current = readLease(store);
  if (!current || current.ownerId !== ownerId) {
    return;
  }
  writeLease(store, {
    ...current,
    expiresAt: now + LOCK_TTL_MS,
  });
}

async function acquireInProcessGate(): Promise<() => void> {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const previous = inProcessTail;
  inProcessTail = previous.then(() => gate);
  await previous;
  return release;
}

export function getKairoCrossContextVoiceOwnerId(): string {
  return ownerId;
}

/** Test helper — drop the shared lease between cases. */
export function resetKairoCrossContextVoiceLockForTests(): void {
  memoryStore.clear();
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(KAIRO_CROSS_CONTEXT_VOICE_LOCK_KEY);
    }
  } catch {
    /* ignore */
  }
}

/**
 * Run `work` while holding the shared voice floor. If the document is hidden,
 * skip without acquiring.
 */
export async function withKairoCrossContextVoiceLock<T>(
  work: () => Promise<T>,
  options: {
    isHidden?: () => boolean;
    storage?: LockStorage;
    onDecision?: (decision: {
      acquired: boolean;
      waitedMs: number;
      skippedHidden: boolean;
      ownerId: string;
      contestedOwnerId: string | null;
    }) => void;
  } = {},
): Promise<{ ran: boolean; result: T | null }> {
  if (options.isHidden?.()) {
    options.onDecision?.({
      acquired: false,
      waitedMs: 0,
      skippedHidden: true,
      ownerId,
      contestedOwnerId: null,
    });
    return { ran: false, result: null };
  }

  const releaseInProcess = await acquireInProcessGate();
  const store = options.storage ?? storage();
  const started = Date.now();
  let contestedOwnerId: string | null = null;

  try {
    while (!tryAcquire(store, Date.now())) {
      const current = readLease(store);
      contestedOwnerId = current?.ownerId ?? contestedOwnerId;
      if (options.isHidden?.()) {
        options.onDecision?.({
          acquired: false,
          waitedMs: Date.now() - started,
          skippedHidden: true,
          ownerId,
          contestedOwnerId,
        });
        return { ran: false, result: null };
      }
      if (Date.now() - started > MAX_WAIT_MS) {
        writeLease(store, {
          ownerId,
          startedAt: Date.now(),
          expiresAt: Date.now() + LOCK_TTL_MS,
        });
        break;
      }
      await delay(POLL_MS);
    }

    options.onDecision?.({
      acquired: true,
      waitedMs: Date.now() - started,
      skippedHidden: false,
      ownerId,
      contestedOwnerId,
    });

    const heartbeat = globalThis.setInterval(() => refreshLease(store), HEARTBEAT_MS);
    try {
      return { ran: true, result: await work() };
    } finally {
      globalThis.clearInterval(heartbeat);
      clearOwnLease(store);
    }
  } finally {
    releaseInProcess();
  }
}
