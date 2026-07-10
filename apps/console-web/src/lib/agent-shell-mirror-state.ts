import { ref } from 'vue';

/** Armed when the operator presses Background on an in-thread shell card. */
export const agentShellMirrorActive = ref(false);

export function armAgentShellMirror(): void {
  agentShellMirrorActive.value = true;
}

export function clearAgentShellMirror(): void {
  agentShellMirrorActive.value = false;
}
