import { apiUrl, fetchJson } from './client';

export type EmailMailboxAccount = {
  account_id: string;
  workspace_id: string;
  email_address: string;
  display_name: string;
  imap: {
    host: string;
    port: number;
    username: string;
    ssl: boolean;
    folder: string;
    password_ref: string;
  };
  smtp: {
    host: string;
    port: number;
    username: string;
    ssl: boolean;
    starttls: boolean;
    from_email: string;
    password_ref: string;
  };
  monitor: {
    enabled: boolean;
    poll_seconds: number;
  };
  updated_at: string;
};

export type EmailOperatorSettings = {
  bridge_enabled: boolean;
  bridge_workspace_id: string;
  stub_enabled: boolean;
  workspace_hint_map: Record<string, string>;
  accounts: EmailMailboxAccount[];
};

export type EmailSettingsSnapshot = {
  settings: EmailOperatorSettings;
  auth: {
    configured: boolean;
    account_count: number;
    locked: boolean;
    bridge_enabled: boolean;
    stub_enabled: boolean;
  };
  projection_path: string;
  account?: EmailMailboxAccount;
  warning?: string;
};

export type EmailAccountUpsertBody = {
  account_id?: string;
  workspace_id: string;
  email_address: string;
  display_name?: string;
  imap_host: string;
  imap_port: number;
  imap_username?: string;
  imap_ssl: boolean;
  imap_folder: string;
  smtp_host: string;
  smtp_port: number;
  smtp_username?: string;
  smtp_ssl: boolean;
  smtp_starttls: boolean;
  smtp_from_email?: string;
  monitor_enabled: boolean;
  poll_seconds: number;
  password_imap?: string;
  password_smtp?: string;
};

export type EmailAccountTestResult = {
  ok: boolean;
  imap: { ok: boolean; detail: string };
  smtp: { ok: boolean; detail: string };
  account_id?: string;
  email_address?: string;
};

export async function fetchEmailSettings(): Promise<EmailSettingsSnapshot> {
  return fetchJson<EmailSettingsSnapshot>(
    '/api/email/settings',
    undefined,
    'email settings load failed',
  );
}

export async function patchEmailSettings(
  patch: Partial<Pick<EmailOperatorSettings, 'bridge_enabled' | 'bridge_workspace_id' | 'stub_enabled' | 'workspace_hint_map'>>,
): Promise<EmailSettingsSnapshot> {
  return fetchJson<EmailSettingsSnapshot>(
    '/api/email/settings',
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    },
    'email settings save failed',
  );
}

export async function upsertEmailAccount(
  body: EmailAccountUpsertBody,
): Promise<EmailSettingsSnapshot> {
  return fetchJson<EmailSettingsSnapshot>(
    '/api/email/accounts',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'email account save failed',
  );
}

export async function deleteEmailAccount(accountId: string): Promise<EmailSettingsSnapshot> {
  const encoded = encodeURIComponent(accountId);
  return fetchJson<EmailSettingsSnapshot>(
    `/api/email/accounts/${encoded}`,
    { method: 'DELETE' },
    'email account delete failed',
  );
}

export async function testEmailAccount(body: {
  account_id?: string;
  password_imap?: string;
  password_smtp?: string;
}): Promise<EmailAccountTestResult> {
  return fetchJson<EmailAccountTestResult>(
    '/api/email/accounts/test',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'email account test failed',
  );
}

export async function suggestEmailReply(body: {
  subject?: string;
  sender?: string;
  text?: string;
  operator_name?: string;
}): Promise<{
  reply_subject: string;
  reply_body: string;
  to: string;
  recommended_action: string;
  recommended_detail: string;
}> {
  return fetchJson(
    '/api/email/suggest-reply',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    'email reply suggest failed',
  );
}

export function emailSettingsUrl(): string {
  return apiUrl('/api/email/settings');
}
