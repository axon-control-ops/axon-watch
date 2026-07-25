/**
 * Deterministic Monday-style illustrated face avatars (SVG data URLs).
 * No external image host — stable per employee/VAXON seed.
 */

export type FaceAvatarKind = 'employee' | 'vaxon';

export type EmployeeFaceAvatarOptions = {
  /** Lead gets a crown + gold rim so the Team strip is scannable. */
  lead?: boolean;
};

const SKIN = ['#f2c7a4', '#e0a878', '#c68642', '#8d5524', '#f5d6c6', '#d4a574'] as const;
const HAIR = ['#1f2430', '#3b2f2f', '#6b4423', '#c4a35a', '#2a4a6e', '#8b3a4a', '#4a5568'] as const;
const SHIRT = ['#2a4a7a', '#1a5a42', '#1f4f6e', '#3d2f6e', '#6a4520', '#0e7490', '#9f1239'] as const;
const BG = ['#123a5c', '#1a3d4a', '#2a2540', '#1e3a2f', '#3a2a1a', '#1a2a3a'] as const;

function hashSeed(seed: string): number {
  let hash = 2166136261;
  for (let i = 0; i < seed.length; i += 1) {
    hash ^= seed.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function pick<T extends readonly string[]>(palette: T, n: number): T[number] {
  return palette[n % palette.length]!;
}

function svgToDataUrl(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/** Illustrated person face — stable for a given seed. */
export function buildEmployeeFaceAvatarUrl(
  seed: string,
  options: EmployeeFaceAvatarOptions = {},
): string {
  const h = hashSeed(seed || 'agent');
  const lead = Boolean(options.lead);
  const skin = pick(SKIN, h);
  const hair = pick(HAIR, h >>> 3);
  const shirt = lead ? '#1e3a5f' : pick(SHIRT, h >>> 6);
  const bg = lead ? '#0c2a45' : pick(BG, h >>> 9);
  const hairStyle = h % 4;
  const smile = h % 3;
  const glasses = lead ? false : (h >>> 12) % 5 === 0;
  const freckles = (h >>> 14) % 4 === 0;

  const hairPath =
    hairStyle === 0
      ? `<ellipse cx="32" cy="22" rx="22" ry="14" fill="${hair}"/>
         <path d="M12 28 Q12 14 32 12 Q52 14 52 28 L48 26 Q32 18 16 26 Z" fill="${hair}"/>`
      : hairStyle === 1
        ? `<path d="M10 34 Q10 12 32 10 Q54 12 54 34 L50 30 Q32 16 14 30 Z" fill="${hair}"/>`
        : hairStyle === 2
          ? `<ellipse cx="32" cy="24" rx="20" ry="16" fill="${hair}"/>
             <rect x="12" y="24" width="40" height="10" rx="4" fill="${hair}"/>`
          : `<path d="M14 36 Q8 18 32 11 Q56 18 50 36 Q44 22 32 20 Q20 22 14 36 Z" fill="${hair}"/>`;

  const mouth =
    smile === 0
      ? `<path d="M24 44 Q32 50 40 44" stroke="#6b3a2a" stroke-width="1.8" fill="none" stroke-linecap="round"/>`
      : smile === 1
        ? `<path d="M25 45 Q32 48 39 45" stroke="#6b3a2a" stroke-width="1.6" fill="none" stroke-linecap="round"/>`
        : `<line x1="26" y1="45" x2="38" y2="45" stroke="#6b3a2a" stroke-width="1.6" stroke-linecap="round"/>`;

  const glassesSvg = glasses
    ? `<g fill="none" stroke="#1e293b" stroke-width="1.4">
         <circle cx="24" cy="36" r="5.2"/>
         <circle cx="40" cy="36" r="5.2"/>
         <path d="M29.2 36 H34.8"/>
       </g>`
    : '';

  const freckleSvg = freckles
    ? `<g fill="#c48a6a" opacity="0.55">
         <circle cx="20" cy="40" r="0.9"/>
         <circle cx="23" cy="42" r="0.8"/>
         <circle cx="44" cy="40" r="0.9"/>
         <circle cx="41" cy="42" r="0.8"/>
       </g>`
    : '';

  const leadChrome = lead
    ? `<circle cx="32" cy="32" r="30" fill="none" stroke="#f0c14b" stroke-width="2.2" opacity="0.9"/>
       <path d="M18 14 L22 8 L27 13 L32 6 L37 13 L42 8 L46 14 L44 18 L20 18 Z" fill="#f0c14b" stroke="#c9a227" stroke-width="0.8"/>
       <circle cx="32" cy="10" r="1.6" fill="#fff4c2"/>`
    : '';

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="32" fill="${bg}"/>
  ${leadChrome}
  <circle cx="32" cy="54" r="18" fill="${shirt}"/>
  <circle cx="32" cy="34" r="16" fill="${skin}"/>
  ${hairPath}
  <ellipse cx="24" cy="36" rx="2.2" ry="2.6" fill="#1f2937"/>
  <ellipse cx="40" cy="36" rx="2.2" ry="2.6" fill="#1f2937"/>
  <ellipse cx="24.6" cy="35.2" rx="0.7" ry="0.8" fill="#f8fafc"/>
  <ellipse cx="40.6" cy="35.2" rx="0.7" ry="0.8" fill="#f8fafc"/>
  <path d="M30.5 39.5 Q32 41 33.5 39.5" stroke="#b8846a" stroke-width="1.1" fill="none" stroke-linecap="round"/>
  ${mouth}
  ${glassesSvg}
  ${freckleSvg}
</svg>`;

  return svgToDataUrl(svg);
}

/** Distinct VAXON operator face — cyan HUD persona, not a human employee. */
export function buildVaxonFaceAvatarUrl(): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <radialGradient id="vxg" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#3ecbff"/>
      <stop offset="70%" stop-color="#0b3a55"/>
      <stop offset="100%" stop-color="#061820"/>
    </radialGradient>
  </defs>
  <rect width="64" height="64" rx="32" fill="url(#vxg)"/>
  <circle cx="32" cy="32" r="22" fill="none" stroke="#7ee7ff" stroke-width="1.2" opacity="0.55"/>
  <circle cx="32" cy="32" r="16" fill="none" stroke="#b8f3ff" stroke-width="0.8" opacity="0.4"/>
  <circle cx="32" cy="30" r="12" fill="#0a2434" stroke="#8be9ff" stroke-width="1.4"/>
  <ellipse cx="26" cy="29" rx="2.4" ry="3" fill="#7af0ff"/>
  <ellipse cx="38" cy="29" rx="2.4" ry="3" fill="#7af0ff"/>
  <path d="M25 37 Q32 42 39 37" stroke="#7af0ff" stroke-width="1.6" fill="none" stroke-linecap="round"/>
  <path d="M20 18 L24 14 M44 14 L48 18" stroke="#7af0ff" stroke-width="1.2" opacity="0.7"/>
</svg>`;
  return svgToDataUrl(svg);
}

export function buildFaceAvatarUrl(
  kind: FaceAvatarKind,
  seed: string,
): string {
  if (kind === 'vaxon') {
    return buildVaxonFaceAvatarUrl();
  }
  return buildEmployeeFaceAvatarUrl(seed);
}
