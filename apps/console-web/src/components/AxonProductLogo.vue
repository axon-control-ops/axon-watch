<script setup lang="ts">
import {
  AXON_PRODUCT_LOGO_PREFIX,
  AXON_PRODUCT_LOGO_SUFFIX,
} from '../lib/operator-persona-name';
</script>

<template>
  <span class="topbar-mockup__logo axon-product-logo">
    <span class="topbar-mockup__logo-prefix">{{ AXON_PRODUCT_LOGO_PREFIX }}</span>
    <span class="topbar-mockup__logo-mark persona-glyph persona-glyph--lg">{{ AXON_PRODUCT_LOGO_SUFFIX }}</span>
  </span>
</template>
