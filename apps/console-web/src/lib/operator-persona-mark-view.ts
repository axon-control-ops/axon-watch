/** Persona mark sizing tokens (typographic VAXON glyph). */

import { OPERATOR_PERSONA_MARK } from './operator-persona-name';

export type PersonaMarkSize = 'xs' | 'sm' | 'md' | 'lg' | 'orb';

export const PERSONA_MARK_SIZE_PX: Record<PersonaMarkSize, number> = {
  xs: 10,
  sm: 13,
  md: 16,
  lg: 20,
  orb: 22,
};

export function createPersonaMarkElement(size: PersonaMarkSize = 'sm'): HTMLSpanElement {
  const mark = document.createElement('span');
  mark.className = `persona-glyph persona-glyph--${size}`;
  mark.setAttribute('aria-hidden', 'true');
  mark.textContent = OPERATOR_PERSONA_MARK;
  return mark;
}
