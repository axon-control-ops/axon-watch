import { computed, type ComputedRef } from 'vue';

import type { CompanyEmployeeRecord } from '../../contracts/canonical';
import {
  resolveDockDeliveryPipelineView,
  type WorkerDeliveryPipelineView,
} from '../../lib/worker-delivery-pipeline-view';

export function useDockDeliveryPipeline(input: {
  receiptLabels: ComputedRef<readonly string[]>;
  employees: ComputedRef<readonly CompanyEmployeeRecord[]>;
}): ComputedRef<WorkerDeliveryPipelineView | null> {
  return computed(() => {
    const employee = input.employees.value.find((row) => row.pipeline_stage);
    return resolveDockDeliveryPipelineView({
      receiptLabels: input.receiptLabels.value,
      employeePipeline: employee
        ? {
            stage: employee.pipeline_stage,
            detail: employee.pipeline_detail,
            draftPrUrl: employee.draft_pr_url,
            ciStatus: employee.ci_status,
          }
        : null,
    });
  });
}
