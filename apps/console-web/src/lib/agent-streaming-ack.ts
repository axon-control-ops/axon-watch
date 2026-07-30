/** Address helpers for agent speech — no canned streaming-ack templates. */

export type AgentAddressForm = 'sir' | 'Sir King' | null;

/** Prefer Sir King for every speaker when addressing the operator. */
export function addressFormForSpeaker(
  kind: 'vaxon' | 'employee' | string | null | undefined,
): AgentAddressForm {
  if (kind === 'employee' || kind === 'vaxon' || kind === 'agent') {
    return 'Sir King';
  }
  return null;
}
