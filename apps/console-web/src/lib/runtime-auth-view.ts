import type { CursorRuntimeStatusSnapshot, RuntimeAuthStatus, RuntimeTargetRecord } from '../api/control-plane';

import type { VaultConsumerRecord } from './vault-surface-view';

export function runtimeAuthMethodLabel(method: string | undefined): string {
  switch (String(method ?? '').trim()) {
    case 'oauth':
      return 'CLI subscription';
    case 'chatgpt':
      return 'ChatGPT login';
    case 'vault_api_key':
      return 'Vault API key';
    case 'api_key':
      return 'Shell API key';
    case 'vault_locked':
      return 'Vault locked';
    case 'vault_missing_key':
      return 'Vault missing key';
    case 'api_key_invalid':
      return 'Invalid API key';
    default:
      return '';
  }
}

export function runtimeAuthAccountLabel(auth: RuntimeAuthStatus | undefined): string {
  let account = String(auth?.account_label ?? '').trim();
  if (account.startsWith('✓')) {
    account = account.replace(/^✓\s*/, '').trim();
  }
  if (account.toLowerCase().startsWith('logged in as ')) {
    account = account.slice('logged in as '.length).trim();
  }
  return account;
}

export function runtimeAuthSummary(auth: RuntimeAuthStatus | undefined): string {
  const message = String(auth?.message ?? '').trim();
  if (message) {
    return message;
  }
  const account = runtimeAuthAccountLabel(auth);
  const method = runtimeAuthMethodLabel(auth?.auth_method);
  if (account && method) {
    return `${method} · ${account}`;
  }
  if (account) {
    return account;
  }
  if (method) {
    return method;
  }
  return auth?.logged_in ? 'Authenticated' : 'Not authenticated';
}

export function composerCursorAuthLine(input: {
  target: RuntimeTargetRecord | null;
  cursorSnapshot: CursorRuntimeStatusSnapshot | null;
}): string {
  const auth = input.cursorSnapshot?.auth ?? input.target?.auth;
  if (!auth) {
    return 'Sign in with `cursor agent login` on the host, or add CURSOR_API_KEY in /vault for headless use.';
  }
  const account = runtimeAuthAccountLabel(auth);
  const method = runtimeAuthMethodLabel(auth.auth_method);
  if (auth.logged_in) {
    if (account && account.includes('@')) {
      return method ? `${method} · ${account}` : account;
    }
    const message = String(auth.message ?? '').trim();
    if (message) {
      return message;
    }
    if (account && method) {
      return `${method} · ${account}`;
    }
    return method || 'Authenticated';
  }
  if (method === 'vault_locked') {
    return 'Unlock /vault to inject provider keys, or run `cursor agent login` on the host.';
  }
  const message = String(auth.message ?? '').trim();
  return message || 'Not authenticated';
}

export function vaultSubscriptionAccountLabel(consumer: VaultConsumerRecord): string {
  const subscription = consumer.subscription_auth;
  if (!subscription?.logged_in) {
    return '';
  }
  return String(subscription.account_label ?? '').trim();
}

export function vaultConsumerAuthSummary(consumer: VaultConsumerRecord): string {
  const account = vaultSubscriptionAccountLabel(consumer);
  if (account) {
    return `CLI subscription · ${account}`;
  }
  const vaultKeys = consumer.satisfied_keys.filter(
    (key) => !key.startsWith('cli_subscription'),
  );
  if (vaultKeys.length) {
    return `Vault keys · ${vaultKeys.join(', ')}`;
  }
  if (consumer.auth_note) {
    return consumer.auth_note;
  }
  return '';
}

export function vaultMissingKeysDisplayLabel(consumer: VaultConsumerRecord): string {
  const labels = consumer.missing_keys.map((item) => {
    if (item === 'subscription_or_api_key') {
      return 'CLI login (`cursor agent login`) or optional CURSOR_API_KEY in /vault';
    }
    if (!item.startsWith('one_of:')) {
      return item;
    }
    const options = item
      .slice('one_of:'.length)
      .split('|')
      .map((value) => value.trim())
      .filter(Boolean);
    return options.length ? `one of ${options.join(' or ')}` : item;
  });
  return labels.join(', ');
}
