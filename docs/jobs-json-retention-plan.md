# jobs.json Retention Plan

## Investigation Summary

`JobManager` persists all jobs to `data/jobs.json` and rewrites the full file on every flush in [src/core/job_manager.py](c:\SDai\SimplyNarrated\src\core\job_manager.py). Persistence is triggered at job creation, queueing, progress updates, cancellation, completion, and failure in the same file. Each persisted job includes its full `activity_log`, even though the status API only returns the last 20 entries in [src/api/routes.py](c:\SDai\SimplyNarrated\src\api\routes.py).

Completed upload jobs are primarily needed while the UI is actively polling status in [static/js/views/progress.js](c:\SDai\SimplyNarrated\static\js\views\progress.js). Chapter reconvert jobs are similarly short-lived polling records in [static/js/views/player.js](c:\SDai\SimplyNarrated\static\js\views\player.js). After completion, the application transitions to library and book metadata rather than relying on long-lived job history.

## Current Data Snapshot

Measured from the current repository state on 2026-04-29, `data/jobs.json` was 8,687 lines and about 308 KB. It held 51 jobs: 48 completed, 2 cancelled, and 1 failed. The oldest job was from 2026-02-25, the newest from 2026-04-18, the average activity history was about 29 entries per job, and the largest activity log had 89 entries.

## Opinion

Do not garbage collect by line count. Line count is tied to JSON formatting and verbose activity logs, not to meaningful application state. The real operational issue is that the entire file is rewritten on each persist, so stale terminal jobs increase write amplification and startup load.

Use age-based retention. Keep active jobs forever while they are `pending` or `processing`, and expire terminal jobs quickly because the application no longer depends on them after work is complete.

## Recommended Policy

1. Use `completed_at` as the primary age reference for completed, failed, and cancelled jobs.
2. Fall back to `created_at` if `completed_at` is missing.
3. Keep terminal jobs for 3 days.
4. Never prune jobs still in `pending` or `processing`.

This keeps the behavior aligned with the UI and avoids deleting records that are still being polled.

## Implementation Plan

1. Add `_prune_jobs()` to [src/core/job_manager.py](c:\SDai\SimplyNarrated\src\core\job_manager.py).
2. Invoke pruning before `_persist_jobs()` writes to disk.
3. Run pruning during startup after `_load_jobs()` and `_recover_jobs_after_restart()`.
4. Make the retention window configurable with `JOB_RETENTION_DAYS=3`.

The immediate effect is that oversized `jobs.json` files shrink on the next write or startup, without changing frontend behavior for active conversions.

## Related File Cleanup

As a follow-up, expired failed or cancelled upload jobs can also clean up stale source files still left under `data/uploads`. That cleanup should not touch anything under `data/library`, because completed book content belongs to the library lifecycle instead of job retention. This distinction matters because upload sources are moved into the library during processing in [src/core/pipeline.py](c:\SDai\SimplyNarrated\src\core\pipeline.py).

## Testing Plan

1. Add a unit test that loads mixed old and recent jobs and verifies only expired terminal jobs are pruned.
2. Add a unit test that confirms active jobs are retained.
3. Add a startup test that verifies old jobs are removed after load and recovery.
4. Add a later test for upload cleanup if file deletion is implemented.

## Recommended Decision

Prune by age, keep terminal jobs for 3 days, and preserve active jobs until they leave `pending` or `processing`. This matches how the application actually uses job records today.
