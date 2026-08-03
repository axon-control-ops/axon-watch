import { describe, expect, it } from 'vitest';

import { buildCodexCatalogRows, codexModelLabel } from './codex-catalog-view';

describe('codex-catalog-view', () => {
  const rows = buildCodexCatalogRows({
    installed: true,
    binary: '/usr/bin/codex',
    auth: { logged_in: true, auth_method: 'chatgpt' },
    available_models: [
      { id: 'gpt-5.5', label: 'GPT-5.5', description: 'Frontier coding model.', badge: 'Medium' },
      { id: 'gpt-5.4-mini', label: 'GPT-5.4-Mini', description: 'Fast coding model.' },
    ],
    codex_models: [],
    catalog_source: 'live',
  });

  it('keeps Auto and the exact models exposed by the signed-in Codex runtime', () => {
    expect(rows.map((row) => row.id)).toEqual(['auto', 'gpt-5.5', 'gpt-5.4-mini']);
    expect(rows[1]?.badge).toBe('Medium');
  });

  it('uses the catalog display name for the selected Codex model', () => {
    expect(codexModelLabel('gpt-5.5', rows)).toBe('GPT-5.5');
    expect(codexModelLabel('auto', rows)).toBe('Auto');
  });
});
