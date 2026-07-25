import { computed, onMounted, ref, watch } from 'vue';

import { fetchSkillsSnapshot, type OperatorSkillsSnapshot } from '../api/skills-api';
import { groupSkillsByWorkspace, skillsSurfaceSummary } from '../lib/skills-surface-view';
import { useAppSurface } from './useAppSurface';

export function useSkillsSurface() {
  const { appSurface } = useAppSurface();
  const snapshot = ref<OperatorSkillsSnapshot | null>(null);
  const loading = ref(false);
  const error = ref('');

  const groups = computed(() => groupSkillsByWorkspace(snapshot.value?.items ?? []));
  const summary = computed(() => skillsSurfaceSummary(snapshot.value));

  async function refresh(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      snapshot.value = await fetchSkillsSnapshot();
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Skills catalog unavailable';
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    if (appSurface.value === 'skills') {
      void refresh();
    }
  });

  watch(appSurface, (surface) => {
    if (surface === 'skills') {
      void refresh();
    }
  });

  return {
    snapshot,
    loading,
    error,
    groups,
    summary,
    refresh,
  };
}
