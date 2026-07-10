import { watch, type Ref } from 'vue';

import {
  buildAgentTerminalMirrorText,
  findAgentTerminalMirrorSegment,
} from '../lib/agent-terminal-mirror';

export type AgentTerminalMirrorHost = {
  writeMirrorSnapshot: (text: string) => void;
};

type MaybeStringRef = Ref<string | null> | Ref<string> | { readonly value: string | null };

export function useAgentTerminalMirror(input: {
  mirrorActive: Ref<boolean>;
  agentSessionId: MaybeStringRef;
  transcriptContent: Ref<string> | { readonly value: string };
  getHost: (sessionId: string) => AgentTerminalMirrorHost | null | undefined;
  clearMirror: () => void;
  streamActive: Ref<boolean>;
}): { syncNow: () => void } {
  let lastSnapshot = '';

  function syncNow(): void {
    if (!input.mirrorActive.value) {
      return;
    }
    const sessionId = input.agentSessionId.value;
    if (!sessionId) {
      return;
    }
    const segment = findAgentTerminalMirrorSegment(input.transcriptContent.value);
    if (!segment) {
      return;
    }
    const snapshot = buildAgentTerminalMirrorText(segment);
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

  watch(
    () => ({
      active: input.mirrorActive.value,
      sessionId: input.agentSessionId.value,
      content: input.transcriptContent.value,
    }),
    () => {
      if (!input.mirrorActive.value) {
        lastSnapshot = '';
        return;
      }
      syncNow();
    },
    { flush: 'post' },
  );

  watch(
    () => input.streamActive.value,
    (streaming, wasStreaming) => {
      if (!wasStreaming || streaming) {
        return;
      }
      if (input.mirrorActive.value) {
        syncNow();
      }
      input.clearMirror();
      lastSnapshot = '';
    },
  );

  return { syncNow };
}
