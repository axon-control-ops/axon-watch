/**
 * Floating VAXON speech chip belongs on Brain Graph (and IDE has its own rail).
 * Mission Control already owns presence in the right LIVE OPERATIONS dock.
 */
export function shouldShowGalaxySpeechCaptions(input: {
  layoutMode: string;
  operatorBrainGalaxyActive: boolean;
}): boolean {
  return input.layoutMode === 'operator' && input.operatorBrainGalaxyActive;
}
