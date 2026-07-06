import { computed, onMounted, ref, watch } from 'vue';

import { fetchDataSnapshot, downloadDataExport } from '../api/control-plane';
import { useAppSurface } from './useAppSurface';
import {
  buildDataSurfaceTables,
  dataSurfaceTotalRows,
  type OperatorDataSnapshot,
} from '../lib/data-surface-view';

export function useDataSurface() {
  const { appSurface } = useAppSurface();
  const snapshot = ref<OperatorDataSnapshot | null>(null);
  const loading = ref(false);
  const error = ref('');
  const exportBusy = ref(false);
  const exportMessage = ref('');

  const tables = computed(() => buildDataSurfaceTables(snapshot.value));
  const totalRows = computed(() => dataSurfaceTotalRows(tables.value));

  async function refresh(): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      const payload = await fetchDataSnapshot();
      snapshot.value = payload.data;
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Operator data unavailable';
    } finally {
      loading.value = false;
    }
  }

  async function exportDiagnostic(): Promise<void> {
    exportBusy.value = true;
    exportMessage.value = '';
    error.value = '';
    try {
      const blob = await downloadDataExport();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = 'axon-operator-data-export.json';
      anchor.click();
      URL.revokeObjectURL(objectUrl);
      exportMessage.value = 'Diagnostic export downloaded.';
    } catch (exc) {
      error.value = exc instanceof Error ? exc.message : 'Diagnostic export failed';
    } finally {
      exportBusy.value = false;
    }
  }

  onMounted(() => {
    if (appSurface.value === 'data') {
      void refresh();
    }
  });

  watch(appSurface, (surface) => {
    if (surface === 'data') {
      void refresh();
    }
  });

  return {
    snapshot,
    loading,
    error,
    tables,
    totalRows,
    exportBusy,
    exportMessage,
    refresh,
    exportDiagnostic,
  };
}
