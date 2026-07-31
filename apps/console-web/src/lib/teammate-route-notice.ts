import { ref } from 'vue';

export type TeammateRouteNotice = {
  reason: string;
  toName: string;
  toRoleLabel: string;
  fromName: string;
  previousEmployeeId: string;
  previousThreadId?: string | null;
  /** When set, the route banner only shows on this IDE thread tab. */
  destinationThreadId?: string | null;
};

/** Shared across IDE composer + Brain/Kairo so Undo survives surface switches. */
export const teammateRouteNotice = ref<TeammateRouteNotice | null>(null);

export function setTeammateRouteNotice(notice: TeammateRouteNotice | null): void {
  teammateRouteNotice.value = notice;
}

export function clearTeammateRouteNotice(): void {
  teammateRouteNotice.value = null;
}

export function teammateRouteNoticeVisibleForThread(
  notice: TeammateRouteNotice,
  currentThreadId: string,
): boolean {
  const destination = notice.destinationThreadId;
  if (destination == null) {
    return true;
  }
  return destination === currentThreadId;
}
