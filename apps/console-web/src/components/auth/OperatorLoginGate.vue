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

const username = ref('operator');
const password = ref('');
const submitting = ref(false);
const submitError = ref<string | null>(null);
const revealPassword = ref(false);
const bodyCopy = computed(() => operatorLoginBodyCopy());
const footerCopy = computed(() =>
  operatorLoginFooterCopy({
    loopbackBypass: props.loopbackBypass,
    cookieMaxAgeSeconds: props.cookieMaxAgeSeconds,
  }),
);
const feedback = computed(() => submitError.value ?? props.connectionError);

async function submit(): Promise<void> {
  const operatorPassword = password.value.trim();
  if (!operatorPassword || submitting.value) {
    return;
  }
  submitting.value = true;
  submitError.value = null;
  try {
    await loginOperatorSession({
      username: username.value.trim(),
      password: operatorPassword,
    });
    password.value = '';
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
        <label for="operator-username">Username</label>
        <input
          id="operator-username"
          v-model="username"
          type="text"
          name="username"
          autocomplete="username"
          autocapitalize="none"
          spellcheck="false"
          :disabled="submitting"
          autofocus
        />
        <label for="operator-password">Password</label>
        <div class="operator-login__password-row">
          <input
            id="operator-password"
            v-model="password"
            :type="revealPassword ? 'text' : 'password'"
            name="password"
            autocomplete="current-password"
            autocapitalize="none"
            spellcheck="false"
            :disabled="submitting"
          />
          <button
            type="button"
            class="operator-login__reveal"
            :aria-label="revealPassword ? 'Hide password' : 'Show password'"
            :aria-pressed="revealPassword"
            @click="revealPassword = !revealPassword"
          >
            {{ revealPassword ? 'Hide' : 'Show' }}
          </button>
        </div>
        <button
          type="submit"
          class="operator-login__submit"
          :disabled="submitting || !password.trim()"
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

.operator-login__password-row {
  display: flex;
  gap: 0.5rem;
  position: relative;
}

.operator-login__form > input,
.operator-login__password-row input {
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
