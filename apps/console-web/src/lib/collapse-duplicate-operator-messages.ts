/** Collapse consecutive identical operator prompts (e.g. Continue re-dispatch). */

export type CollapsibleOperatorMessage = {
  role?: string | null;
  content?: string | null;
  attachments?: Array<{ attachment_id?: string | null }> | null;
};

function attachmentSignature(
  attachments: CollapsibleOperatorMessage['attachments'],
): string {
  if (!attachments?.length) {
    return '';
  }
  return attachments
    .map((item) => String(item.attachment_id ?? '').trim())
    .filter(Boolean)
    .join('|');
}

function isDuplicateOperatorPrompt(
  left: CollapsibleOperatorMessage,
  right: CollapsibleOperatorMessage,
): boolean {
  if (left.role !== 'operator' || right.role !== 'operator') {
    return false;
  }
  const leftText = String(left.content ?? '').trim();
  const rightText = String(right.content ?? '').trim();
  if (!leftText || leftText !== rightText) {
    return false;
  }
  return attachmentSignature(left.attachments) === attachmentSignature(right.attachments);
}

/** Keep the newest copy when Continue/resend repeats the same YOU turn. */
export function collapseConsecutiveDuplicateOperatorMessages<T extends CollapsibleOperatorMessage>(
  messages: readonly T[],
): T[] {
  const out: T[] = [];
  for (const message of messages) {
    const previous = out[out.length - 1];
    if (previous && isDuplicateOperatorPrompt(previous, message)) {
      out[out.length - 1] = message;
      continue;
    }
    out.push(message);
  }
  return out;
}

/** Index of the latest operator message for Cursor-like sticky pin. */
export function latestOperatorMessageIndex(
  items: ReadonlyArray<{ kind?: string; message?: { role?: string | null } | null }>,
): number {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    const item = items[index];
    if ((item?.kind === 'message' || !item?.kind) && item?.message?.role === 'operator') {
      return index;
    }
  }
  return -1;
}
