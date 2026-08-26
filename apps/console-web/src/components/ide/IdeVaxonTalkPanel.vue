<script setup lang="ts">
import KairoConversationBar from '../../features/kairo-conversation/KairoConversationBar.vue';
import { openOperatorStandup } from '../../features/kairo-conversation/open-operator-standup';
import PersonaTitle from '../PersonaTitle.vue';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();

function closePanel(): void {
  shell.closeIdeBriefingPanel();
}

async function requestFleetReport(): Promise<void> {
  await openOperatorStandup(shell);
}
</script>

<template>
  <section
    id="ide-vaxon-talk-panel"
    class="ide-vaxon-talk-panel hud-panel-frame"
    aria-label="Talk to VAXON"
  >
    <div class="ide-vaxon-talk-panel__heading panel-heading">
      <div class="ide-vaxon-talk-panel__intro">
        <p class="panel-heading__title">
          <PersonaTitle suffix="Voice" mark-size="xs" />
        </p>
        <p class="ide-vaxon-talk-panel__hint">
          Ask a question, dispatch work, or request a fresh fleet report.
        </p>
      </div>
      <div class="ide-vaxon-talk-panel__heading-actions">
        <button
          type="button"
          class="ide-vaxon-talk-panel__report"
          title="Generate a fresh VAXON fleet report"
          @click="requestFleetReport"
        >
          Fleet report
        </button>
        <button
          type="button"
          class="ide-vaxon-talk-panel__close"
          aria-label="Close VAXON talk panel"
          title="Close"
          @click="closePanel"
        >
          ×
        </button>
      </div>
    </div>
    <div class="ide-vaxon-talk-panel__body">
      <KairoConversationBar />
    </div>
  </section>
</template>

<style scoped>
.ide-vaxon-talk-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.ide-vaxon-talk-panel__heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.35rem 0.5rem 0.15rem;
}

.ide-vaxon-talk-panel__intro {
  min-width: 0;
}

.ide-vaxon-talk-panel__hint {
  margin: 0.18rem 0 0;
  color: var(--text-muted);
  font-size: 0.62rem;
  line-height: 1.35;
}

.ide-vaxon-talk-panel__heading-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.35rem;
}

.ide-vaxon-talk-panel__report,
.ide-vaxon-talk-panel__close {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 1rem;
  line-height: 1;
  padding: 0.15rem 0.45rem;
}

.ide-vaxon-talk-panel__report {
  color: rgba(255, 210, 128, 0.96);
  cursor: pointer;
  font-size: 0.62rem;
  letter-spacing: 0.04em;
  padding: 0.28rem 0.55rem;
  text-transform: uppercase;
}

.ide-vaxon-talk-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 0.35rem 0.35rem;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar) {
  min-height: 0;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__command-row) {
  align-items: stretch;
  flex-direction: column;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__form) {
  display: grid;
  grid-template-areas:
    "glyph input input input input"
    "attach mic . ask dispatch";
  grid-template-columns: auto auto minmax(0, 1fr) auto auto;
  border-radius: 0.75rem;
  padding: 0.55rem;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__glyph-slot) {
  grid-area: glyph;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__input) {
  grid-area: input;
  width: 100%;
  min-height: 1.9rem;
  font-size: 0.72rem;
}

.ide-vaxon-talk-panel__body :deep(.vaxon-attach--button) {
  grid-area: attach;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__mic) {
  grid-area: mic;
}

.ide-vaxon-talk-panel__body
  :deep(.kairo-conversation-bar__send:not(.kairo-conversation-bar__send--dispatch)) {
  grid-area: ask;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__send--dispatch) {
  grid-area: dispatch;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__run-orbit) {
  justify-content: flex-start;
  width: 100%;
}

.ide-vaxon-talk-panel__body :deep(.kairo-conversation-bar__error) {
  border-left: 2px solid rgba(255, 120, 96, 0.72);
  border-radius: 0.25rem;
  background: rgba(255, 96, 72, 0.08);
  padding: 0.42rem 0.55rem;
  line-height: 1.4;
}
</style>
