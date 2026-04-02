# Live-Run Regression Matrix

<!--
retry_result values (source of truth: live_run_retry.LIVE_RUN_RETRY_RESULT_VALUES):
  not_requested  — retry_budget == 0, task did not request retry
  not_needed     — retry_budget > 0, first attempt succeeded, retry unused
  not_attempted  — retry_budget > 0, first attempt failed, retry not yet executed
                    (includes partial summaries with no driver_result)
  recovered      — retry executed and task succeeded
                    (legacy "retried" + succeeded normalized to this)
  exhausted      — retry budget consumed, task still failed
                    (legacy "retried" + failed normalized to this)
  null           — no summary.json found (missing run)

retry-overview.json notes:
  retry_result_counts has fixed 5 keys (the non-null enum above).
  Missing-summary tasks (retry_result == null) contribute to task_count
  but are excluded from all retry_result_counts values.
-->

| task_id | task_name | lane | model_provider | result | failure_status | failure_layer | failure_stage | duration_sec | retry_result | retry_budget | retry_attempts_used | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| queue-queue-smoke | queue smoke: complete a simple linux housekeeper run | benchmark |  | completed |  |  |  |  | not_needed | 2 | 0 | sample baseline row |
