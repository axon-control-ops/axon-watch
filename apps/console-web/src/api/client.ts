/** Default budget for control-plane JSON calls so hung CLI probes cannot stall the shell forever. */
export const DEFAULT_FETCH_TIMEOUT_MS = 12_000;

/** Inbox waits on watch monitor/connector probes; cold polls can exceed 12s after revive. */
export const INBOX_FETCH_TIMEOUT_MS = 30_000;

/** Brain graph may wait on a cold watch inbox + connectors; keep above the default. */
export const BRAIN_GRAPH_FETCH_TIMEOUT_MS = 30_000;

/** Runtime status / auth refresh can wait on `cursor agent status` (~7s) plus Codex probes. */
export const RUNTIME_STATUS_FETCH_TIMEOUT_MS = 30_000;

/** Thread history can include dozens of large agent transcripts; keep above normalize+transfer. */
export const THREAD_HISTORY_FETCH_TIMEOUT_MS = 45_000;

export class ApiRequestError extends Error {
  readonly status: number;
  readonly label: string;

  constructor(label: string, status: number) {
    super(label);
    this.name = 'ApiRequestError';
    this.label = label;
    this.status = status;
  }
}

export function isApiNotFoundError(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 404;
}

export function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  return '';
}

export function apiUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const baseUrl = controlPlaneBaseUrl();
  return baseUrl ? `${baseUrl}${normalized}` : normalized;
}

function mergeAbortSignals(
  timeoutMs: number,
  external?: AbortSignal | null,
): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort(new DOMException(`request timed out after ${timeoutMs}ms`, 'TimeoutError'));
  }, timeoutMs);

  const onExternalAbort = () => {
    controller.abort(external?.reason);
  };
  if (external) {
    if (external.aborted) {
      onExternalAbort();
    } else {
      external.addEventListener('abort', onExternalAbort, { once: true });
    }
  }

  return {
    signal: controller.signal,
    clear: () => {
      clearTimeout(timer);
      external?.removeEventListener('abort', onExternalAbort);
    },
  };
}

export async function fetchJson<T>(
  path: string,
  init: RequestInit = {},
  errorLabel?: string,
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS,
): Promise<T> {
  const { signal, clear } = mergeAbortSignals(timeoutMs, init.signal);
  const startedAt = performance.now();
  try {
    const response = await fetch(apiUrl(path), { ...init, signal });
    if (!response.ok) {
      throw new ApiRequestError(
        errorLabel ?? `request failed with status ${response.status}`,
        response.status,
      );
    }
    return (await response.json()) as T;
  } catch (error) {
    // #region agent log
    fetch('http://127.0.0.1:7706/ingest/90bcaec2-2b39-4d4a-84b5-157c12735440',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'fc0b35'},body:JSON.stringify({sessionId:'fc0b35',runId:'frontend-api',hypothesisId:'H2',location:'api/client.ts:fetchJson-catch',message:'frontend API request failed',data:{path,method:init.method ?? 'GET',status:error instanceof ApiRequestError ? error.status : null,errorName:error instanceof Error ? error.name : typeof error,elapsedMs:Math.round(performance.now()-startedAt),aborted:signal.aborted},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new Error(errorLabel ?? `request timed out after ${timeoutMs}ms`);
    }
    if (error instanceof Error && error.name === 'AbortError') {
      // Caller-supplied cancellation must not be mislabeled as a timeout.
      if (init.signal?.aborted) {
        throw error;
      }
      throw new Error(errorLabel ?? `request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clear();
  }
}

export async function fetchBlob(
  path: string,
  init: RequestInit = {},
  errorLabel?: string,
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS,
): Promise<Blob> {
  const { signal, clear } = mergeAbortSignals(timeoutMs, init.signal);
  try {
    const response = await fetch(apiUrl(path), { ...init, signal });
    if (!response.ok) {
      throw new Error(errorLabel ?? `request failed with status ${response.status}`);
    }
    return response.blob();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new Error(errorLabel ?? `request timed out after ${timeoutMs}ms`);
    }
    if (error instanceof Error && error.name === 'AbortError') {
      if (init.signal?.aborted) {
        throw error;
      }
      throw new Error(errorLabel ?? `request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clear();
  }
}

export async function postJson<T>(
  path: string,
  body?: unknown,
  errorLabel?: string,
): Promise<T> {
  return fetchJson<T>(
    path,
    {
      method: 'POST',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    errorLabel,
  );
}
