import { normalizePersonaSttAliases } from './operator-persona-stt-aliases';

/** Operator-facing persona label for Axon-X (internal modules may still use kairo_*). */

export const OPERATOR_PERSONA_NAME = 'VAXON';

/**
 * Phonetic form for TTS so neural voices do not letter-spell V-A-X-O-N.
 * Spoken as “vek-son” / “Vaxon” — never “V A X O N”.
 */
export const OPERATOR_PERSONA_SPOKEN_NAME = 'Vekson';

/** Expanded name shown on boot / persona surfaces. */
export const OPERATOR_PERSONA_BACKRONYM = 'Voice AI Assistant';

/** LIVE OPERATIONS orb stage tagline (Mission Control). */
export const OPERATOR_PERSONA_OPS_TAGLINE =
  'Second brain · manager · prioritizes · you decide';

/** Dotted label rendered inside the galaxy orb core. */
export const OPERATOR_PERSONA_ORB_LABEL = 'V.A.X.O.N';

/** Product logo suffix for AXON-X (not the persona name). */
export const AXON_PRODUCT_LOGO_PREFIX = 'AXON-';
export const AXON_PRODUCT_LOGO_SUFFIX = 'X';

/** Compact glyph for tight HUD chips. */
export const OPERATOR_PERSONA_MARK = 'V';

export const OPERATOR_PERSONA_WAKE_WORD_RE =
  /\b(vaxon|naxon|axon[\s-]?vaxon|x|kairo|cairo|kyro|kairos|ex)\b/i;

export function personaStatusLabel(mode: string, personaName: string = OPERATOR_PERSONA_NAME): string {
  const name = personaName.trim() || OPERATOR_PERSONA_NAME;
  return `${name} · ${mode}`;
}

export function personaThreadPrefix(
  body: string,
  personaName: string = OPERATOR_PERSONA_NAME,
): string {
  const name = personaName.trim() || OPERATOR_PERSONA_NAME;
  const trimmed = body.trim();
  if (!trimmed) {
    return `${name} — Agent is working…`;
  }
  return `${name} — ${trimmed}`;
}

export function stripPersonaWakeWordPrefix(text: string): string {
  return normalizePersonaSttAliases(text)
    .replace(OPERATOR_PERSONA_WAKE_WORD_RE, '')
    .trim()
    .replace(/^[,.\-–—:!?]+/, '')
    .trim();
}
