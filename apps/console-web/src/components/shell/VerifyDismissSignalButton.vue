<script setup lang="ts">
import { computed, ref } from 'vue';

import { canVerifyDismissHandoffSignal } from '../../lib/signal-handoff-dismiss';
import { useShellStore } from '../../stores/shell';

const props = defineProps<{
  signalId: string;
  compact?: boolean;
}>();

const shell = useShellStore();
const pending = ref(false);

const inboxItems = computed(() =>
  shell.inboxItems.map((item) => ({ signal_id: item.signal_id })),
);

const gate = computed(() => canVerifyDismissHandoffSignal(props.signalId, inboxItems.value));

const disabled = computed(
  () =>
    pending.value ||
    shell.signalClearState === 'clearing' ||
    !gate.value.allowed,
);

const title = computed(() => gate.value.reason ?? 'Dismiss this signal after the monitor is healthy.');

async function handleClick(): Promise<void> {
  if (disabled.value) {
    return;
  }

  pending.value = true;
  try {
    await shell.verifyAndDismissHandoffSignal(props.signalId);
  } finally {
    pending.value = false;
  }
}
</script>

<template>
  <button
    type="button"
    class="verify-dismiss-signal-button"
    :class="{ 'verify-dismiss-signal-button--compact': compact }"
    :disabled="disabled"
    :title="title"
    @click.stop="handleClick"
  >
    {{
      pending || shell.signalClearState === 'clearing'
        ? 'Verifying…'
        : 'Verify & dismiss'
    }}
  </button>
</template>

<style scoped>
.verify-dismiss-signal-button {
  border: 1px solid rgba(72, 255, 196, 0.35);
  border-radius: 0.35rem;
  background: rgba(72, 255, 196, 0.08);
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  padding: 0.3rem 0.55rem;
}

.verify-dismiss-signal-button--compact {
  font-size: 0.62rem;
  padding: 0.24rem 0.45rem;
}

.verify-dismiss-signal-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
