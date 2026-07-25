import { onBeforeUnmount, ref, watch, type Ref } from 'vue';

import type { IdeQuickGuide } from '../lib/ide-quick-guide';

const IDE_QUICK_GUIDE_HOLD_MS = 800;

function ideQuickGuideIdentity(guide: IdeQuickGuide): string {
  return [guide.tone, guide.title, ...guide.steps, ...guide.actions.map((action) => action.id)].join(
    '\x1f',
  );
}

/** Sticky + dismissible IDE tip chrome for the editor stack. */
export function useIdeQuickGuideSticky(ideQuickGuide: Ref<IdeQuickGuide | null>): {
  ideQuickGuideSticky: Ref<IdeQuickGuide | null>;
  dismissIdeQuickGuide: () => void;
} {
  const ideQuickGuideSticky = ref<IdeQuickGuide | null>(null);
  const ideQuickGuideDismissedIdentity = ref<string | null>(null);
  let ideQuickGuideClearTimer: ReturnType<typeof setTimeout> | null = null;

  function dismissIdeQuickGuide(): void {
    if (ideQuickGuideSticky.value) {
      ideQuickGuideDismissedIdentity.value = ideQuickGuideIdentity(ideQuickGuideSticky.value);
    }
    if (ideQuickGuideClearTimer !== null) {
      clearTimeout(ideQuickGuideClearTimer);
      ideQuickGuideClearTimer = null;
    }
    ideQuickGuideSticky.value = null;
  }

  watch(
    ideQuickGuide,
    (next) => {
      if (next) {
        if (ideQuickGuideClearTimer !== null) {
          clearTimeout(ideQuickGuideClearTimer);
          ideQuickGuideClearTimer = null;
        }
        const nextIdentity = ideQuickGuideIdentity(next);
        if (ideQuickGuideDismissedIdentity.value === nextIdentity) {
          ideQuickGuideSticky.value = null;
          return;
        }
        const previous = ideQuickGuideSticky.value;
        if (!previous || ideQuickGuideIdentity(previous) !== nextIdentity) {
          ideQuickGuideSticky.value = next;
        }
        return;
      }
      if (!ideQuickGuideSticky.value || ideQuickGuideClearTimer !== null) {
        return;
      }
      ideQuickGuideClearTimer = setTimeout(() => {
        ideQuickGuideSticky.value = null;
        ideQuickGuideClearTimer = null;
      }, IDE_QUICK_GUIDE_HOLD_MS);
    },
    { immediate: true },
  );

  onBeforeUnmount(() => {
    if (ideQuickGuideClearTimer !== null) {
      clearTimeout(ideQuickGuideClearTimer);
      ideQuickGuideClearTimer = null;
    }
  });

  return { ideQuickGuideSticky, dismissIdeQuickGuide };
}
