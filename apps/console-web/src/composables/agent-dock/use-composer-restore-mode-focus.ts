import { nextTick, type Ref, watch } from 'vue';

import { consumeIdeComposerModeRequest } from '../../lib/ide-composer-restore-request';
import type { ComposerMode } from './use-composer-menus';

/** Apply Edit/Resend mode switch when the shell bumps commandFocusToken. */
export function useComposerRestoreModeFocus(options: {
  commandFocusToken: () => number;
  composerMode: Ref<ComposerMode>;
  inputRef: Ref<HTMLTextAreaElement | null>;
  syncComposerHeight: () => void;
}): void {
  const { commandFocusToken, composerMode, inputRef, syncComposerHeight } = options;

  watch(commandFocusToken, () => {
    const requestedMode = consumeIdeComposerModeRequest();
    if (requestedMode) {
      composerMode.value = requestedMode;
    }
    void nextTick(() => {
      syncComposerHeight();
      inputRef.value?.focus();
    });
  });
}
