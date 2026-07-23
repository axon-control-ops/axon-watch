import { watch, type Ref } from 'vue';

import {
  buildAgentTerminalMirrorScrollback,
  findAgentTerminalMirrorSegment,
  listAgentTerminalMirrorSegments,
  terminalMirrorSignature,
} from '../lib/agent-terminal-mirror';
import { agentShellMirrorForcedText } from '../lib/agent-shell-mirror-state';

export type AgentTerminalMirrorHost = {
  writeMirrorSnapshot: (text: string) => void;
  exitMirrorMode?: () => void;
  writeInput?: (data: string) => void;
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
    const content = input.getTranscriptContent();
    const segment = findAgentTerminalMirrorSegment(content);
    // Live open shells must win over a pinned snapshot from a prior turn/card,
    // otherwise OTA/`npm run …` mirrors stay stuck on stale output.
    if (segment?.open) {
      return buildAgentTerminalMirrorScrollback(content);
    }
    const forced = forcedText.value?.trim();
    if (forced) {
      return forced.endsWith('\n') ? forced : `${forced}\n`;
    }
    return buildAgentTerminalMirrorScrollback(content);
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
      const content = input.getTranscriptContent();
      const hasOpenTerminal = listAgentTerminalMirrorSegments(content).some(
        (segment) => segment.open,
      );
      if (forcedText.value && !hasOpenTerminal) {
        return {
          active: true as const,
          sessionId: input.agentSessionId.value,
          contentLen: -1,
          terminalSig: '',
          forced: forcedText.value,
        };
      }
      return {
        active: true as const,
        sessionId: input.agentSessionId.value,
        contentLen: content.length,
        contentTail: content.slice(-240),
        terminalSig: terminalMirrorSignature(content),
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
      // Final paint, then pin the snapshot so remounts do not fall back to an idle agent PTY.
      if (input.mirrorActive.value) {
        syncNow();
        const snapshot = resolveSnapshot();
        if (snapshot && !forcedText.value) {
          forcedText.value = snapshot;
        }
      }
      input.clearMirror();
    },
  );

  return { syncNow };
}
