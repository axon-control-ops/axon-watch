import { describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';

import { useAgentTerminalMirror } from './useAgentTerminalMirror';

describe('useAgentTerminalMirror', () => {
  it('writes a forced snapshot into the agent host', async () => {
    const mirrorActive = ref(true);
    const agentSessionId = ref<string | null>('term-agent');
    const streamActive = ref(true);
    const forcedText = ref<string | null>('$ curl http://127.0.0.1:8787/api/kairo/tts\nok\n');
    const writeMirrorSnapshot = vi.fn();
    const exitMirrorMode = vi.fn();

    const { syncNow } = useAgentTerminalMirror({
      mirrorActive,
      agentSessionId,
      getTranscriptContent: () => '',
      streamActive,
      clearMirror: () => {
        mirrorActive.value = false;
      },
      forcedText,
      getHost: () => ({ writeMirrorSnapshot, exitMirrorMode }),
    });

    syncNow();

    expect(writeMirrorSnapshot).toHaveBeenCalledWith(
      '$ curl http://127.0.0.1:8787/api/kairo/tts\nok\n',
    );
    expect(exitMirrorMode).not.toHaveBeenCalled();
  });

  it('keeps mirrored content when the stream ends instead of wiping the host', async () => {
    const mirrorActive = ref(true);
    const agentSessionId = ref<string | null>('term-agent');
    const streamActive = ref(true);
    const forcedText = ref<string | null>(null);
    const writeMirrorSnapshot = vi.fn();
    const exitMirrorMode = vi.fn();
    const transcript = [
      ':::terminal cd /tmp && ls',
      'file.txt',
      ':::',
    ].join('\n');

    useAgentTerminalMirror({
      mirrorActive,
      agentSessionId,
      getTranscriptContent: () => transcript,
      streamActive,
      clearMirror: () => {
        mirrorActive.value = false;
      },
      forcedText,
      getHost: () => ({ writeMirrorSnapshot, exitMirrorMode }),
    });

    streamActive.value = false;
    await nextTick();

    expect(writeMirrorSnapshot).toHaveBeenCalled();
    expect(exitMirrorMode).not.toHaveBeenCalled();
    expect(mirrorActive.value).toBe(false);
    expect(forcedText.value).toContain('$ cd /tmp && ls');
  });

  it('prefers a live open terminal over a stale forced snapshot', () => {
    const mirrorActive = ref(true);
    const agentSessionId = ref<string | null>('term-agent');
    const streamActive = ref(true);
    const forcedText = ref<string | null>('$ old ota\nprevious log\n');
    const writeMirrorSnapshot = vi.fn();
    const transcript = ref(
      [':::terminal RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota', '# Publish OTA'].join('\n'),
    );

    const { syncNow } = useAgentTerminalMirror({
      mirrorActive,
      agentSessionId,
      getTranscriptContent: () => transcript.value,
      streamActive,
      clearMirror: () => {
        mirrorActive.value = false;
      },
      forcedText,
      getHost: () => ({ writeMirrorSnapshot }),
    });

    syncNow();

    expect(writeMirrorSnapshot).toHaveBeenCalledWith(
      '$ RELEASE_GUARD_ALLOW_DIRTY=1 npm run ota\n# Publish OTA\nrunning…\n',
    );
  });

  it('keeps a deliberate forced snapshot when transcript terminals are closed', () => {
    const forcedText = ref<string | null>('$ selected command\nselected output\n');
    const writeMirrorSnapshot = vi.fn();
    const transcript = [':::terminal npm test', 'historical output', ':::'].join('\n');

    const { syncNow } = useAgentTerminalMirror({
      mirrorActive: ref(true),
      agentSessionId: ref<string | null>('term-agent'),
      getTranscriptContent: () => transcript,
      streamActive: ref(false),
      clearMirror: vi.fn(),
      forcedText,
      getHost: () => ({ writeMirrorSnapshot }),
    });

    syncNow();

    expect(writeMirrorSnapshot).toHaveBeenCalledWith('$ selected command\nselected output\n');
  });
});
