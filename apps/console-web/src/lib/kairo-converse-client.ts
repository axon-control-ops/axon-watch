function controlPlaneBaseUrl(): string {
  const configured = import.meta.env.VITE_CONTROL_PLANE_BASE_URL;
  return typeof configured === 'string' ? configured.replace(/\/$/, '') : '';
}

export type KairoConverseTurnKind =
  | 'status_question'
  | 'open_question'
  | 'command'
  | 'chat'
  | 'action';
export type KairoConverseSource = 'template' | 'model' | 'fallback';
export type KairoConverseAnswerTier = 'fast' | 'deep';

export type KairoConverseAction =
  | {
      type: 'handoff_signal';
      signal_id: string;
      target_workspace_id: string;
      task: string;
      employee_id?: string | null;
      employee_role?: string | null;
      employee_name?: string | null;
      routing_receipt?: string | null;
      model_receipt?: Record<string, unknown> | null;
    }
  | {
      type: 'route_employee';
      target_workspace_id: string;
      task: string;
      employee_id: string;
      employee_role: string;
      employee_name: string;
      routing_receipt?: string | null;
      model_receipt?: Record<string, unknown> | null;
    }
  | {
      type: 'dispatch_command';
      content: string;
    }
  | {
      type: 'focus_briefing';
    }
  | {
      type: 'move_voice_orb';
      dock?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
      mode?: 'smart_dodge';
    };

export interface KairoConverseArtifactAction {
  label: string;
  ui_action: Record<string, unknown> | null;
}

export interface KairoConverseArtifactSource {
  label: string;
  detail: string;
}

export interface KairoConverseArtifact {
  artifact_id: string;
  title: string;
  summary: string;
  body: string;
  sources: KairoConverseArtifactSource[];
  actions: KairoConverseArtifactAction[];
}

export interface KairoConverseRequest {
  content: string;
  session_id?: string;
  workspace_id?: string;
  use_runtime?: boolean;
  answer_tier?: KairoConverseAnswerTier;
  context_workspace_id?: string;
  context_signal_id?: string;
  context_node_id?: string;
}

export interface KairoConverseResponse {
  turn_kind: KairoConverseTurnKind;
  reply: string;
  source: KairoConverseSource;
  command_content: string | null;
  requires_confirmation?: boolean | null;
  action_tier?: string | null;
  dispatch_lane?: string | null;
  voice_routing_mode?: string | null;
  routing_receipt?: string | null;
  model_receipt?: Record<string, unknown> | null;
  action: KairoConverseAction | null;
  artifacts: KairoConverseArtifact[];
}

/** Fast-path converse budget — never leave the UI latched in thinking. */
export const KAIRO_CONVERSE_FAST_TIMEOUT_MS = 8_000;
/** Deep/runtime converse budget — progress then abort with a spoken fallback. */
export const KAIRO_CONVERSE_DEEP_TIMEOUT_MS = 20_000;

export class KairoConverseTimeoutError extends Error {
  readonly timeoutMs: number;

  constructor(timeoutMs: number) {
    super(`KAIRO converse timed out after ${timeoutMs}ms`);
    this.name = 'KairoConverseTimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

export function resolveKairoConverseTimeoutMs(
  answerTier: KairoConverseAnswerTier | undefined,
  overrideMs?: number,
): number {
  if (typeof overrideMs === 'number' && overrideMs > 0) {
    return overrideMs;
  }
  return answerTier === 'deep' ? KAIRO_CONVERSE_DEEP_TIMEOUT_MS : KAIRO_CONVERSE_FAST_TIMEOUT_MS;
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

export async function postKairoConverse(
  body: KairoConverseRequest,
  options?: { signal?: AbortSignal | null; timeoutMs?: number },
): Promise<KairoConverseResponse> {
  const timeoutMs = resolveKairoConverseTimeoutMs(body.answer_tier, options?.timeoutMs);
  const baseUrl = controlPlaneBaseUrl();
  const url = baseUrl ? `${baseUrl}/api/kairo/converse` : '/api/kairo/converse';
  const { signal, clear } = mergeAbortSignals(timeoutMs, options?.signal);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
    if (!response.ok) {
      throw new Error(`KAIRO converse failed (${response.status})`);
    }
    return (await response.json()) as KairoConverseResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new KairoConverseTimeoutError(timeoutMs);
    }
    if (error instanceof Error && error.name === 'AbortError') {
      if (options?.signal?.aborted) {
        throw error;
      }
      throw new KairoConverseTimeoutError(timeoutMs);
    }
    throw error;
  } finally {
    clear();
  }
}

export function converseTimeoutFallbackReply(timeoutMs: number): string {
  const seconds = Math.max(1, Math.round(timeoutMs / 1000));
  return `I could not finish that within ${seconds} seconds. Try a shorter question, or ask again when the runtime is free.`;
}
