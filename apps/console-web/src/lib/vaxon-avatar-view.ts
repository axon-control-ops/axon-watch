import { buildVaxonFaceAvatarUrl } from '../features/workspace-agents/employee-face-avatar';

/** Public cinematic portrait with SVG fallback when the asset fails to load. */
export const VAXON_PORTRAIT_URL = '/vaxon-portrait.jpg';

export function resolveVaxonAvatarUrl(): string {
  return VAXON_PORTRAIT_URL;
}

export function resolveVaxonAvatarFallbackUrl(): string {
  return buildVaxonFaceAvatarUrl();
}

export const VAXON_AVATAR_ALT = 'VAXON operator persona';
