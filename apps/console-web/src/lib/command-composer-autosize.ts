export const COMMAND_COMPOSER_MIN_LINES = 2;
export const COMMAND_COMPOSER_MAX_LINES_COMPACT = 8;
export const COMMAND_COMPOSER_MAX_LINES_DEFAULT = 12;

export function resolveCommandComposerMaxLines(compact: boolean): number {
  return compact ? COMMAND_COMPOSER_MAX_LINES_COMPACT : COMMAND_COMPOSER_MAX_LINES_DEFAULT;
}

export function resizeCommandComposer(
  textarea: HTMLTextAreaElement,
  options: { compact?: boolean } = {},
): void {
  const maxLines = resolveCommandComposerMaxLines(options.compact ?? false);
  textarea.style.height = '0px';

  const styles = getComputedStyle(textarea);
  const lineHeight = Number.parseFloat(styles.lineHeight) || 20;
  const paddingTop = Number.parseFloat(styles.paddingTop) || 0;
  const paddingBottom = Number.parseFloat(styles.paddingBottom) || 0;
  const borderTop = Number.parseFloat(styles.borderTopWidth) || 0;
  const borderBottom = Number.parseFloat(styles.borderBottomWidth) || 0;

  const minHeight =
    lineHeight * COMMAND_COMPOSER_MIN_LINES + paddingTop + paddingBottom + borderTop + borderBottom;
  const maxHeight =
    lineHeight * maxLines + paddingTop + paddingBottom + borderTop + borderBottom;
  const scrollHeight = textarea.scrollHeight;
  const nextHeight = Math.min(maxHeight, Math.max(minHeight, scrollHeight));

  textarea.style.height = `${nextHeight}px`;
  textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
}

export function resetCommandComposerHeight(textarea: HTMLTextAreaElement, compact = false): void {
  textarea.value = '';
  resizeCommandComposer(textarea, { compact });
}
