/** Whether the in-chat terminal card should show its output body. */
export function shouldShowConversationTerminalOutput(options: {
  hasOutput: boolean;
  open: boolean;
  streaming: boolean;
  mirrored: boolean;
  expandedInChat: boolean;
}): boolean {
  if (!options.hasOutput) {
    return false;
  }
  // Live open shells keep growing chat output even when the dock mirrors.
  if (options.open && options.streaming) {
    return true;
  }
  if (options.mirrored && !options.expandedInChat) {
    return false;
  }
  return true;
}
