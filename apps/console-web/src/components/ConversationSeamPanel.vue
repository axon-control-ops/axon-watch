<script setup lang="ts">
import { useShellStore } from '../stores/shell';

const shell = useShellStore();
</script>

<template>
  <div class="conversation-seam">
    <ul v-if="shell.threadMessages.length" class="conversation-seam__list">
      <li
        v-for="message in shell.threadMessages"
        :key="message.message_id"
        class="conversation-seam__item"
        :class="`conversation-seam__item--${message.role}`"
      >
        <div class="conversation-seam__meta">
          <span class="conversation-seam__role">{{ message.role }}</span>
          <time class="conversation-seam__time" :datetime="message.created_at">
            {{ message.created_at }}
          </time>
        </div>
        <p
          v-if="message.role !== 'agent'"
          class="conversation-seam__content"
        >
          {{ message.content }}
        </p>
        <pre
          v-else
          class="conversation-seam__content conversation-seam__content--agent"
        >{{ message.content }}</pre>
      </li>
    </ul>
    <p v-else class="region-copy">No active conversation</p>
  </div>
</template>
