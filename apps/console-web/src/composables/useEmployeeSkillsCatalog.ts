import { ref, shallowRef } from 'vue';

import { fetchSkillsSnapshot, type OperatorSkillRecord } from '../api/skills-api';

let cachedSkills: OperatorSkillRecord[] | null = null;
let inflight: Promise<OperatorSkillRecord[]> | null = null;

export function useEmployeeSkillsCatalog() {
  const skills = shallowRef<OperatorSkillRecord[]>(cachedSkills ?? []);
  const loading = ref(false);
  const error = ref('');

  async function ensureLoaded(): Promise<void> {
    if (cachedSkills) {
      skills.value = cachedSkills;
      return;
    }
    if (inflight) {
      skills.value = await inflight;
      return;
    }
    loading.value = true;
    error.value = '';
    inflight = fetchSkillsSnapshot()
      .then((snapshot) => snapshot.items)
      .catch((exc) => {
        error.value = exc instanceof Error ? exc.message : 'Skills catalog unavailable';
        return [] as OperatorSkillRecord[];
      })
      .finally(() => {
        loading.value = false;
        inflight = null;
      });
    cachedSkills = await inflight;
    skills.value = cachedSkills;
  }

  return {
    skills,
    loading,
    error,
    ensureLoaded,
  };
}
