/**
 * Post-wake / streaming STT adapter surface.
 * Clip-cloud and browser capture remain the production fallbacks in kairo-shared-speech-capture.
 */

export type StreamingSttStatus = 'idle' | 'connecting' | 'streaming' | 'finalizing' | 'error';

export interface StreamingSttPartial {
  text: string;
  isFinal: boolean;
  at: number;
}

export interface StreamingSttAdapter {
  readonly id: string;
  status(): StreamingSttStatus;
  start(options: {
    onPartial: (partial: StreamingSttPartial) => void;
    onError?: (message: string) => void;
  }): Promise<void>;
  stop(): Promise<string | null>;
}

/**
 * Placeholder adapter — returns null finals so callers fall back to clip/browser STT.
 * Real Azure streaming can replace this behind the same interface after latency evidence.
 */
export class DeferredStreamingSttAdapter implements StreamingSttAdapter {
  readonly id = 'deferred-streaming-stt';
  private current: StreamingSttStatus = 'idle';

  status(): StreamingSttStatus {
    return this.current;
  }

  async start(): Promise<void> {
    this.current = 'idle';
  }

  async stop(): Promise<string | null> {
    this.current = 'idle';
    return null;
  }
}

export function createPostWakeSttAdapter(): StreamingSttAdapter {
  return new DeferredStreamingSttAdapter();
}
