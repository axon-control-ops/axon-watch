<script setup lang="ts">
import WorkbenchIcon from '../WorkbenchIcon.vue';

defineProps<{ open: boolean }>();

const emit = defineEmits<{
  create: [kind: 'bash' | 'zsh' | 'vaxon'];
  toggle: [];
}>();
</script>

<template>
  <div class="terminal-tabbar__new-wrap">
    <div class="terminal-tabbar__new-group" role="group" aria-label="New terminal">
      <button
        type="button"
        class="terminal-tabbar__action-button terminal-tabbar__action-button--new"
        title="New Terminal"
        aria-label="New Terminal"
        @click.stop="emit('create', 'zsh')"
      >
        <WorkbenchIcon name="plus" class="terminal-tabbar__action" :size="16" />
      </button>
      <button
        type="button"
        class="terminal-tabbar__action-button terminal-tabbar__action-button--profile"
        title="Launch Profile…"
        aria-label="Launch Profile"
        aria-haspopup="menu"
        :aria-expanded="open"
        @click.stop="emit('toggle')"
      >
        <WorkbenchIcon name="chevron-down" class="terminal-tabbar__action" :size="12" />
      </button>
    </div>
    <div v-if="open" class="terminal-tabbar__new-menu" role="menu" aria-label="Launch Profile">
      <button
        v-for="profile in [
          { kind: 'zsh' as const, icon: 'shell-zsh' as const, label: 'zsh · local' },
          { kind: 'bash' as const, icon: 'shell-bash' as const, label: 'bash · local' },
          { kind: 'vaxon' as const, icon: 'terminal-agent' as const, label: 'vaxon · agent' },
        ]"
        :key="profile.kind"
        type="button"
        class="terminal-tabbar__new-menu-item"
        :class="{ 'terminal-tabbar__new-menu-item--agent': profile.kind === 'vaxon' }"
        role="menuitem"
        @click="emit('create', profile.kind)"
      >
        <WorkbenchIcon :name="profile.icon" :size="14" />
        <span>{{ profile.label }}</span>
      </button>
    </div>
  </div>
</template>
