import { agentContentHasTranscriptBlocks } from '../lib/agent-transcript-blocks';
import { findAgentTerminalMirrorSegment } from '../lib/agent-terminal-mirror';

type ThreadLike = {
  message_id: string;
  role: string;
  content: string;
};

/** Resolve the agent transcript content used for terminal mirroring. */
export function resolveAgentTerminalMirrorTranscript(options: {
  streamMessageId: string | null | undefined;
  threadMessages: ThreadLike[];
}): string {
  const streamId = options.streamMessageId;
  if (streamId) {
    return (
      options.threadMessages.find((message) => message.message_id === streamId)?.content ?? ''
    );
  }
  for (let index = options.threadMessages.length - 1; index >= 0; index -= 1) {
    const message = options.threadMessages[index];
    if (message?.role !== 'agent') {
      continue;
    }
    if (
      agentContentHasTranscriptBlocks(message.content) &&
      findAgentTerminalMirrorSegment(message.content)
    ) {
      return message.content;
    }
  }
  return '';
}
