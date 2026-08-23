<script setup lang="ts">
import { computed, ref } from 'vue';

import { loginOperatorSession } from '../../api/operator-auth-api';
import {
  operatorLoginBodyCopy,
  operatorLoginFooterCopy,
} from '../../lib/operator-login-copy';
import AxonProductLogo from '../AxonProductLogo.vue';

const props = withDefaults(
  defineProps<{
    checking?: boolean;
    connectionError?: string | null;
    loopbackBypass?: boolean;
    cookieMaxAgeSeconds?: number | null;
  }>(),
  {
    checking: false,
    connectionError: null,
    loopbackBypass: false,
    cookieMaxAgeSeconds: null,
  },
);

const emit = defineEmits<{
  authenticated: [];
  retry: [];
}>();

const operatorToken = ref('');
const submitting = ref(false);
const submitError = ref<string | null>(null);
const revealToken = ref(false);
const bodyCopy = computed(() => operatorLoginBodyCopy());
const footerCopy = computed(() =>
  operatorLoginFooterCopy({
    loopbackBypass: props.loopbackBypass,
    cookieMaxAgeSeconds: props.cookieMaxAgeSeconds,
  }),
);
const feedback = computed(() => submitError.value ?? props.connectionError);

async function submit(): Promise<void> {
  const token = operatorToken.value.trim();
  if (!token || submitting.value) {
    return;
  }
  submitting.value = true;
  submitError.value = null;
  try {
    await loginOperatorSession(token);
    operatorToken.value = '';
    emit('authenticated');
  } catch (error) {
    submitError.value =
      error instanceof Error ? error.message : 'Operator sign-in failed.';
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="operator-login" aria-labelledby="operator-login-title">
    <section class="operator-login__card">
      <header class="operator-login__header">
        <AxonProductLogo />
        <p class="operator-login__eyebrow">SECURE OPERATOR ACCESS</p>
        <h1 id="operator-login-title">Sign in to Axon-X</h1>
        <p>{{ bodyCopy }}</p>
      </header>

      <div v-if="checking" class="operator-login__status" role="status">
        Checking operator session…
      </div>

      <form v-else class="operator-login__form" @submit.prevent="submit">
        <label for="operator-token">Operator token</label>
        <div class="operator-login__token-row">
          <input
            type="text"
            name="username"
            value="axon-x-operator"
            autocomplete="username"
            class="operator-login__username"
            tabindex="-1"
            aria-hidden="true"
          />
          <input
            id="operator-token"
            v-model="operatorToken"
            :type="revealToken ? 'text' : 'password'"
            name="password"
            autocomplete="current-password"
            autocapitalize="none"
            spellcheck="false"
            :disabled="submitting"
            autofocus
          />
          <button
            type="button"
            class="operator-login__reveal"
            :aria-label="revealToken ? 'Hide token' : 'Show token'"
            :aria-pressed="revealToken"
            @click="revealToken = !revealToken"
          >
            {{ revealToken ? 'Hide' : 'Show' }}
          </button>
        </div>
        <button
          type="submit"
          class="operator-login__submit"
          :disabled="submitting || !operatorToken.trim()"
        >
          {{ submitting ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>

      <p v-if="feedback" class="operator-login__error" role="alert">{{ feedback }}</p>
      <button
        v-if="connectionError && !checking"
        type="button"
        class="operator-login__retry"
        @click="emit('retry')"
      >
        Retry session check
      </button>

      <footer>{{ footerCopy }}</footer>
    </section>
  </main>
</template>

<style scoped>
.operator-login {
  align-items: center;
  background:
    radial-gradient(circle at 50% 18%, rgba(0, 242, 255, 0.12), transparent 34rem),
    #030b11;
  box-sizing: border-box;
  color: #d8faff;
  display: flex;
  min-height: 100vh;
  padding: 1.25rem;
  position: relative;
}

.operator-login__card {
  background: rgba(4, 18, 27, 0.96);
  border: 1px solid rgba(0, 242, 255, 0.45);
  border-radius: 0.75rem;
  box-shadow: 0 0 3rem rgba(0, 242, 255, 0.12);
  margin: auto;
  max-width: 30rem;
  padding: clamp(1.25rem, 4vw, 2rem);
  width: 100%;
}

.operator-login__header h1 {
  font-size: clamp(1.5rem, 5vw, 2.15rem);
  margin: 0.65rem 0;
}

.operator-login__header > p:last-child,
.operator-login footer {
  color: #8db5bd;
  line-height: 1.55;
}

.operator-login__eyebrow {
  color: #00f2ff;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  margin: 1.25rem 0 0;
}

.operator-login__form {
  display: grid;
  gap: 0.65rem;
  margin-top: 1.5rem;
}

.operator-login__form label {
  color: #bdeef4;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.operator-login__token-row {
  display: flex;
  gap: 0.5rem;
  position: relative;
}

.operator-login__username {
  height: 0;
  left: 0;
  margin: 0;
  opacity: 0;
  padding: 0;
  pointer-events: none;
  position: absolute;
  width: 0;
}

.operator-login__token-row input {
  background: #02080d;
  border: 1px solid rgba(0, 242, 255, 0.38);
  border-radius: 0.35rem;
  color: #ecfdff;
  flex: 1;
  font: inherit;
  min-width: 0;
  padding: 0.75rem;
}

.operator-login button {
  border: 1px solid rgba(0, 242, 255, 0.5);
  border-radius: 0.35rem;
  cursor: pointer;
  font: inherit;
}

.operator-login button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.operator-login__reveal,
.operator-login__retry {
  background: transparent;
  color: #8feaf1;
  padding: 0.65rem 0.85rem;
}

.operator-login__submit {
  background: #00dbe7;
  color: #021014;
  font-weight: 700;
  padding: 0.75rem 1rem;
}

.operator-login__error {
  background: rgba(255, 88, 88, 0.09);
  border: 1px solid rgba(255, 88, 88, 0.35);
  border-radius: 0.35rem;
  color: #ffaaaa;
  line-height: 1.4;
  margin: 1rem 0 0;
  padding: 0.75rem;
}

.operator-login__status {
  color: #8feaf1;
  margin-top: 1.5rem;
}

.operator-login__retry {
  margin-top: 0.75rem;
}

.operator-login footer {
  border-top: 1px solid rgba(0, 242, 255, 0.12);
  font-size: 0.76rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
}
</style>
