<script setup lang="ts">
import { useId } from 'vue';

import { AXON_PRODUCT_LOGO_PREFIX } from '../lib/operator-persona-name';

const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
const gradId = `axonProductXGrad-${uid}`;
const glowId = `axonProductXGlow-${uid}`;
</script>

<template>
  <span class="topbar-mockup__logo axon-product-logo" aria-label="Axon-X">
    <span class="topbar-mockup__logo-prefix">{{ AXON_PRODUCT_LOGO_PREFIX }}</span>
    <svg
      class="topbar-mockup__logo-mark axon-product-logo__x"
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient :id="gradId" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#e8fbff" />
          <stop offset="50%" stop-color="#48c4ff" />
          <stop offset="100%" stop-color="#00f2ff" />
        </linearGradient>
        <filter :id="glowId" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="2.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <g
        fill="none"
        :stroke="`url(#${gradId})`"
        stroke-width="9"
        stroke-linecap="round"
        :filter="`url(#${glowId})`"
      >
        <path d="M14 14 L50 50" />
        <path d="M50 14 L14 50" />
      </g>
      <circle cx="32" cy="32" r="3.2" fill="#9ef0ff" />
    </svg>
  </span>
</template>
