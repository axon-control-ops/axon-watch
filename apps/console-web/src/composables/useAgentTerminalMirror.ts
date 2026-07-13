import { watch, type Ref } from 'vue';

import {
  buildAgentTerminalMirrorText,
  findAgentTerminalMirrorSegment,
} from '../lib/agent-terminal-mirror';
import { agentShellMirrorForcedText } from '../lib/agent-shell-mirror-state';

export type AgentTerminalMirrorHost = {
  writeMirrorSnapshot: (text: string) => void;
  exitMirrorMode?: () => void;
};

type MaybeStringRef = Ref<string | null> | Ref<string> | { readonly value: string | null };

export function useAgentTerminalMirror(input: {
  mirrorActive: Ref<boolean>;
  agentSessionId: MaybeStringRef;
  /** Prefer a cheap getter — only read while mirror is armed. */
  getTranscriptContent: () => string;
  getHost: (sessionId: string) => AgentTerminalMirrorHost | null | undefined;
  clearMirror: () => void;
  streamActive: Ref<boolean>;
  forcedText?: Ref<string | null>;
}): { syncNow: () => void } {
  let lastSnapshot = '';
  let syncFrame: number | null = null;
  const forcedText = input.forcedText ?? agentShellMirrorForcedText;

  function resolveSnapshot(): string | null {
    const forced = forcedText.value?.trim();
    if (forced) {
      return forced.endsWith('\n') ? forced : `${forced}\n`;
    }
    const segment = findAgentTerminalMirrorSegment(input.getTranscriptContent());
    if (!segment) {
      return null;
    }
    return buildAgentTerminalMirrorText(segment);
  }

  function syncNow(): void {
    if (!input.mirrorActive.value) {
      return;
    }
    const sessionId = input.agentSessionId.value;
    if (!sessionId) {
      return;
    }
    const snapshot = resolveSnapshot();
    if (!snapshot) {
      return;
    }
    if (snapshot === lastSnapshot) {
      return;
    }
    const host = input.getHost(sessionId);
    if (!host) {
      return;
    }
    lastSnapshot = snapshot;
    host.writeMirrorSnapshot(snapshot);
  }

  function scheduleSync(): void {
    if (syncFrame !== null) {
      return;
    }
    const schedule =
      typeof requestAnimationFrame === 'function'
        ? requestAnimationFrame
        : (cb: FrameRequestCallback) => globalThis.setTimeout(cb, 16) as unknown as number;
    syncFrame = schedule(() => {
      syncFrame = null;
      syncNow();
    });
  }

  watch(
    () => {
      // Forced snapshots are stable — do not re-read the growing transcript every delta.
      if (!input.mirrorActive.value) {
        return {
          active: false as const,
          sessionId: input.agentSessionId.value,
          contentLen: -1,
          forced: forcedText.value,
        };
      }
      if (forcedText.value) {
        return {
          active: true as const,
          sessionId: input.agentSessionId.value,
          contentLen: -1,
          forced: forcedText.value,
        };
      }
      const content = input.getTranscriptContent();
      return {
        active: true as const,
        sessionId: input.agentSessionId.value,
        contentLen: content.length,
        contentTail: content.slice(-240),
        forced: null as string | null,
      };
    },
    (next) => {
      if (!next.active) {
        // Keep the last mirrored shell on screen. Exiting mirror mode reconnects an
        // empty agent PTY and is what made the bottom panel look blank.
        lastSnapshot = '';
        return;
      }
      scheduleSync();
    },
    { flush: 'post' },
  );

  watch(
    () => input.streamActive.value,
    (streaming, wasStreaming) => {
      if (!wasStreaming || streaming) {
        return;
      }
      // Final paint, then stop watching further deltas — but leave the snapshot visible.
      if (input.mirrorActive.value) {
        syncNow();
      }
      input.clearMirror();
    },
  );

  return { syncNow };
}
