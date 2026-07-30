import type { OperatorThreadEntry } from './operator-thread';

/** One Cursor-like chat turn: sticky YOU prompt + following agent/system replies. */
export type IdeConversationTurn = {
  id: string;
  prompt: OperatorThreadEntry | null;
  replies: OperatorThreadEntry[];
};

function attachmentSignature(message: OperatorThreadEntry): string {
  const attachments = message.attachments ?? [];
  if (!attachments.length) {
    return '';
  }
  return attachments
    .map((item) => String(item.attachment_id ?? '').trim())
    .filter(Boolean)
    .join('|');
}

/** Identity for resend/regenerate collapse — text + attachment set. */
export function operatorPromptIdentity(message: OperatorThreadEntry): string {
  return `${String(message.content ?? '').trim()}\0${attachmentSignature(message)}`;
}

/**
 * Group a flat IDE thread into turns so sticky YOU prompts are scoped to their
 * turn containing-block. When the next turn reaches the top, CSS sticky pushes
 * the previous prompt away (Cursor behavior).
 *
 * Resending the same YOU prompt (Retry / inline Send) replaces the previous
 * turn instead of stacking a duplicate sticky box — Cursor regenerate parity.
 */
export function groupIdeConversationTurns(
  messages: readonly OperatorThreadEntry[],
): IdeConversationTurn[] {
  const turns: IdeConversationTurn[] = [];
  let current: IdeConversationTurn | null = null;

  for (const message of messages) {
    if (message.role === 'operator') {
      const identity = operatorPromptIdentity(message);
      if (
        current?.prompt &&
        identity &&
        identity === operatorPromptIdentity(current.prompt)
      ) {
        current.id = message.message_id;
        current.prompt = message;
        current.replies = [];
        continue;
      }
      current = {
        id: message.message_id,
        prompt: message,
        replies: [],
      };
      turns.push(current);
      continue;
    }

    if (!current) {
      current = {
        id: `orphan_${message.message_id}`,
        prompt: null,
        replies: [message],
      };
      turns.push(current);
      continue;
    }

    current.replies.push(message);
  }

  return turns;
}
