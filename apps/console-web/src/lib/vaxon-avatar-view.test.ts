import { describe, expect, it } from 'vitest';

import { resolveVaxonAvatarFallbackUrl, resolveVaxonAvatarUrl } from './vaxon-avatar-view';

describe('vaxon avatar view', () => {
  it('prefers the cinematic portrait asset', () => {
    expect(resolveVaxonAvatarUrl()).toBe('/vaxon-portrait.jpg');
  });

  it('keeps an SVG data-url fallback', () => {
    expect(resolveVaxonAvatarFallbackUrl().startsWith('data:image/svg+xml')).toBe(true);
  });
});
