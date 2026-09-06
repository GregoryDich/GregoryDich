-- SnapPlay AI scheduled maintenance (pg_cron).
--
-- Run once per project after db/migrations have been applied and the pg_cron
-- extension is enabled (see config.md §4). Safe to re-run: every job is
-- unscheduled before it is scheduled again, so no duplicates accumulate.
--
-- Requires from db/migrations:
--   public.expire_credits()          returns int   (contract §6)
--   public.reap_stale_jobs(int)      releases reservations of jobs stuck in
--                                    `running` longer than the given seconds
--   jobs.expires_at / job_assets     (contract §2 `expires_at`, §6 tables)
-- credit_ledger.job_id must be declared ON DELETE SET NULL (it is nullable per
-- contract §3) so that purging jobs never fails on the ledger.

create extension if not exists pg_cron;

select cron.unschedule(jobid)
from cron.job
where jobname in (
    'snapplay_expire_credits',
    'snapplay_reap_stale_jobs',
    'snapplay_purge_expired_jobs'
);

-- Credit grants past their expires_at become ledger `expire` entries.
select cron.schedule(
    'snapplay_expire_credits',
    '7 * * * *',
    $$select public.expire_credits();$$
);

-- Database-side counterpart of the AWS reaper task: a worker that died
-- mid-job must never silently consume a credit (contract §10).
select cron.schedule(
    'snapplay_reap_stale_jobs',
    '* * * * *',
    $$select public.reap_stale_jobs(180);$$
);

-- Finished jobs and their asset rows are dropped once the 24 h signed-URL
-- window has closed. Storage objects are removed by the backend cleanup
-- (Supabase Storage) or the S3 lifecycle rule (AWS), not here.
select cron.schedule(
    'snapplay_purge_expired_jobs',
    '*/15 * * * *',
    $$
    delete from public.job_assets a
    using public.jobs j
    where a.job_id = j.id
      and j.expires_at < now()
      and j.status in ('succeeded', 'failed', 'cancelled');

    delete from public.jobs j
    where j.expires_at < now()
      and j.status in ('succeeded', 'failed', 'cancelled');
    $$
);
