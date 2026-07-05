<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

import {
  OPERATOR_SUPPORTED_COMMANDS,
  type OperatorSupportedCommand,
} from '../../lib/operator-supported-commands';
import { useShellStore } from '../../stores/shell';

const shell = useShellStore();
const open = ref(false);
const copiedExample = ref<string | null>(null);
const triggerRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const panelStyle = ref<Record<string, string>>({});

let copiedTimer: number | undefined;

function syncPanelPosition(): void {
  const trigger = triggerRef.value;
  if (!trigger || typeof window === 'undefined') {
    return;
  }

  const rect = trigger.getBoundingClientRect();
  const panelWidth = Math.min(384, window.innerWidth - 32);
  const left = Math.min(Math.max(16, rect.right - panelWidth), window.innerWidth - panelWidth - 16);

  panelStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    bottom: `${window.innerHeight - rect.top + 8}px`,
    width: `${panelWidth}px`,
    zIndex: '6000',
  };
}

function togglePanel(): void {
  open.value = !open.value;
}

function closePanel(): void {
  open.value = false;
}

function handleDocumentPointerDown(event: PointerEvent): void {
  if (!open.value) {
    return;
  }

  const target = event.target as Node;
  if (triggerRef.value?.contains(target) || panelRef.value?.contains(target)) {
    return;
  }

  closePanel();
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    closePanel();
  }
}

async function copyExample(example: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(example);
    copiedExample.value = example;
    if (copiedTimer) {
      window.clearTimeout(copiedTimer);
    }
    copiedTimer = window.setTimeout(() => {
      copiedExample.value = null;
    }, 1600);
  } catch {
    copiedExample.value = null;
  }
}

function useExample(example: string): void {
  void copyExample(example);
  shell.focusCommandSeam(example);
  closePanel();
}

function commandLabel(command: OperatorSupportedCommand): string {
  return command.examples.join(' · ');
}

watch(open, async (isOpen) => {
  if (!isOpen) {
    window.removeEventListener('resize', syncPanelPosition);
    window.removeEventListener('scroll', syncPanelPosition, true);
    return;
  }

  await nextTick();
  syncPanelPosition();
  window.addEventListener('resize', syncPanelPosition);
  window.addEventListener('scroll', syncPanelPosition, true);
});

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  document.addEventListener('keydown', handleEscape);
});

onUnmounted(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  document.removeEventListener('keydown', handleEscape);
  window.removeEventListener('resize', syncPanelPosition);
  window.removeEventListener('scroll', syncPanelPosition, true);
  if (copiedTimer) {
    window.clearTimeout(copiedTimer);
  }
});
</script>

<template>
  <div ref="triggerRef" class="supported-commands-footer">
    <button
      type="button"
      class="status-bar-mockup__chip status-bar-mockup__chip--commands"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="dialog"
      title="Show supported operator commands (exact text for the Command tab)"
      @click.stop="togglePanel"
    >
      <span class="status-bar-mockup__icon status-bar-mockup__icon--commands" aria-hidden="true" />
      <span class="status-bar-mockup__chip-label">Commands</span>
    </button>

    <Teleport to="body">
      <section
        v-if="open"
        ref="panelRef"
        class="supported-commands-footer__panel supported-commands-footer__panel--teleport"
        :style="panelStyle"
        role="dialog"
        aria-label="Supported operator commands"
        @click.stop
      >
        <header class="supported-commands-footer__header">
          <div>
            <p class="supported-commands-footer__title">Supported commands</p>
            <p class="supported-commands-footer__subtitle">
              Exact text for the Command tab (right dock). Not free-form chat yet.
            </p>
          </div>
          <button type="button" class="supported-commands-footer__close" @click="closePanel">
            Close
          </button>
        </header>

        <ul class="supported-commands-footer__list">
          <li
            v-for="command in OPERATOR_SUPPORTED_COMMANDS"
            :key="command.id"
            class="supported-commands-footer__item"
          >
            <div class="supported-commands-footer__copy">
              <p class="supported-commands-footer__command">{{ commandLabel(command) }}</p>
              <p class="supported-commands-footer__description">{{ command.description }}</p>
            </div>
            <div class="supported-commands-footer__actions">
              <button
                v-for="example in command.examples"
                :key="example"
                type="button"
                class="supported-commands-footer__action"
                @click="useExample(example)"
              >
                {{ copiedExample === example ? 'Copied' : 'Use' }}
              </button>
            </div>
          </li>
        </ul>
      </section>
    </Teleport>
  </div>
</template>
