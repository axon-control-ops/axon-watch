<script setup lang="ts">
import { computed } from 'vue';

import { renderAgentMessageMarkdown } from '../../lib/agent-message-markdown';
import { handleMarkdownContainerClick } from '../../lib/markdown-link-click';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  leadName: string;
  title: string;
  intro: string;
  bodyMarkdown: string;
  confidence: string | null;
  verificationNotice: string | null;
  workspaceId?: string | null;
}>();

const shell = useShellStore();

const displayLeadName = computed(() => {
  if (props.leadName && props.leadName !== 'Lead') {
    return props.leadName;
  }
  return shell.activeIdeEmployee?.name?.trim() || props.leadName || 'Lead';
});

const introHtml = computed(() =>
  props.intro.trim()
    ? renderAgentMessageMarkdown(props.intro, { workspaceId: props.workspaceId })
    : '',
);
const bodyHtml = computed(() =>
  renderAgentMessageMarkdown(props.bodyMarkdown, { workspaceId: props.workspaceId }),
);
const noticeHtml = computed(() =>
  props.verificationNotice
    ? renderAgentMessageMarkdown(props.verificationNotice, {
        workspaceId: props.workspaceId,
      })
    : '',
);

function handleMarkdownClick(event: MouseEvent): void {
  handleMarkdownContainerClick(event, {
    openWorkspaceFile: (path) => shell.openWorkspaceFile(path),
  });
}
</script>

<template>
  <article class="lead-standup" data-mode="standup">
    <header class="lead-standup__head">
      <div class="lead-standup__identity">
        <span class="lead-standup__mark" aria-hidden="true" />
        <div class="lead-standup__titles">
          <p class="lead-standup__kicker">Lead {{ title }}</p>
          <p class="lead-standup__lead">{{ displayLeadName }}</p>
        </div>
      </div>
      <span v-if="confidence" class="lead-standup__confidence">Confidence {{ confidence }}</span>
    </header>

    <div
      v-if="introHtml"
      class="lead-standup__intro conversation-seam__content conversation-seam__content--markdown"
      v-html="introHtml"
      @click="handleMarkdownClick"
    />

    <div
      class="lead-standup__body conversation-seam__content conversation-seam__content--markdown"
      v-html="bodyHtml"
      @click="handleMarkdownClick"
    />

    <aside v-if="noticeHtml" class="lead-standup__notice" aria-label="Verification notice">
      <p class="lead-standup__notice-label">Verification notice</p>
      <div
        class="conversation-seam__content conversation-seam__content--markdown"
        v-html="noticeHtml"
        @click="handleMarkdownClick"
      />
    </aside>
  </article>
</template>

<style scoped>
.lead-standup {
  display: grid;
  gap: 0.55rem;
  margin: 0.15rem 0 0.35rem;
  padding: 0.7rem 0.75rem 0.65rem;
  border: 1px solid rgba(90, 210, 255, 0.28);
  border-radius: 0.7rem;
  background:
    radial-gradient(ellipse at 8% 0%, rgba(0, 170, 255, 0.16), transparent 45%),
    radial-gradient(ellipse at 90% 100%, rgba(120, 90, 255, 0.08), transparent 40%),
    rgba(2, 12, 20, 0.88);
  box-shadow:
    inset 0 0 0 1px rgba(120, 230, 255, 0.06),
    0 0 1.1rem rgba(0, 140, 200, 0.14);
}

.lead-standup__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.55rem;
}

.lead-standup__identity {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
}

.lead-standup__mark {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: rgba(90, 230, 255, 0.95);
  box-shadow: 0 0 0.7rem rgba(0, 220, 255, 0.55);
  flex: 0 0 auto;
}

.lead-standup__titles {
  min-width: 0;
}

.lead-standup__kicker {
  margin: 0;
  color: rgba(140, 220, 245, 0.88);
  font: 650 0.55rem/1.1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.lead-standup__lead {
  margin: 0.12rem 0 0;
  color: rgba(236, 250, 255, 0.98);
  font: 700 0.95rem/1.15 var(--font-display, ui-sans-serif, system-ui);
  letter-spacing: 0.02em;
}

.lead-standup__confidence {
  flex: 0 0 auto;
  padding: 0.22rem 0.5rem;
  border: 1px solid rgba(100, 220, 160, 0.35);
  border-radius: 999px;
  background: rgba(0, 40, 28, 0.55);
  color: rgba(170, 255, 210, 0.95);
  font: 650 0.58rem/1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.04em;
}

.lead-standup__intro :deep(p:first-child),
.lead-standup__body :deep(p:first-child) {
  margin-top: 0;
}

.lead-standup__notice {
  margin-top: 0.15rem;
  padding: 0.5rem 0.55rem;
  border: 1px solid rgba(255, 180, 90, 0.28);
  border-radius: 0.45rem;
  background: rgba(40, 24, 0, 0.35);
}

.lead-standup__notice-label {
  margin: 0 0 0.3rem;
  color: rgba(255, 200, 120, 0.92);
  font: 650 0.55rem/1.1 var(--font-mono, ui-monospace, monospace);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
</style>
