-- The support read view (contract §15; 0006): one row per profile with the numbers a
-- support macro needs, readable by service_role and by nobody else.
\set ON_ERROR_STOP on

create function pg_temp.morph(p_user uuid) returns uuid
language plpgsql as $$
declare
  v_job public.jobs;
begin
  v_job := public.create_job(p_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.start_job(v_job.id, 'worker');
  perform public.complete_job(v_job.id, '{}'::jsonb);
  return v_job.id;
end;
$$;

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000d101';
  v_friend uuid := '00000000-0000-4000-8000-00000000d102';
  v_bare uuid := '00000000-0000-4000-8000-00000000d103';
  v_code text;
  v_job1 uuid;
  v_job2 uuid;
  v_failed public.jobs;
  v_row record;
begin
  insert into auth.users (id, email) values (v_user, 'support-user@test.local'), (v_bare, 'support-bare@test.local');
  select code into v_code from public.user_referral_codes where user_id = v_user;
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_friend, 'support-friend@test.local', jsonb_build_object('referral_code', v_code));

  perform public.record_purchase(v_user, 'paddle', 'txn-sv1', 'pack_50', 900, 800, null, '{}'::jsonb, 'paddle:txn:sv1');
  perform public.record_purchase(v_user, 'paddle', 'txn-sv2', 'pack_50', 900, 800, null, '{}'::jsonb, 'paddle:txn:sv2');
  perform public.apply_purchase_refund('paddle', 'txn-sv2', 'requested_by_customer');
  v_job1 := pg_temp.morph(v_user);
  v_job2 := pg_temp.morph(v_user);
  v_failed := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_failed.id, '{"code":"internal_error","message":"boom"}'::jsonb);
  perform public.create_api_key(v_user, 'ci');
  perform public.revoke_api_key(id, v_user) from public.create_api_key(v_user, 'old');
  perform public.submit_nps(v_user, 8, null);
  perform public.record_job_feedback(v_job1, v_user, 'up', null, null, 1200);
  perform public.record_job_feedback(v_job2, v_user, 'down', 'bleed', null, null);
  perform public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);  -- one credit reserved

  select * into v_row from public.support_user_overview where user_id = v_user;
  assert found, 'no overview row';
  assert v_row.email = 'support-user@test.local' and v_row.plan = 'credits' and v_row.deleted_at is null
     and v_row.created_at is not null, format('identity %s', v_row);
  -- 3 + 50 + 50 - 50 (refund) - 2 (captures) + 1 (feedback refund) = 52 credits, 1 reserved
  assert v_row.balance = 52 and v_row.reserved = 1, format('balance %s/%s', v_row.balance, v_row.reserved);
  assert v_row.morphs_total = 2 and v_row.last_morph_at = (select finished_at from public.jobs where id = v_job2),
    format('morphs %s', v_row);
  assert v_row.purchases = 2 and v_row.refunds = 1, format('purchases %s refunds %s', v_row.purchases, v_row.refunds);
  assert v_row.api_keys = 1, format('api keys %s', v_row.api_keys);
  assert v_row.nps_score = 8, format('nps %s', v_row.nps_score);
  assert v_row.feedback_up = 1 and v_row.feedback_down = 1 and v_row.feedback_refunds = 1, format('feedback %s', v_row);
  assert v_row.referral_code = v_code and v_row.referred_by is null and v_row.friends_joined = 1,
    format('referral %s', v_row);

  -- the friend's row points back; a bare account is all zeros and nulls
  select * into v_row from public.support_user_overview where email = 'support-friend@test.local';
  assert v_row.user_id = v_friend and v_row.referred_by = v_user and v_row.balance = 5, format('friend %s', v_row);
  select * into v_row from public.support_user_overview where user_id = v_bare;
  assert v_row.balance = 3 and v_row.reserved = 0 and v_row.morphs_total = 0 and v_row.last_morph_at is null
     and v_row.purchases = 0 and v_row.refunds = 0 and v_row.api_keys = 0 and v_row.nps_score is null
     and v_row.feedback_up = 0 and v_row.feedback_down = 0 and v_row.friends_joined = 0
     and v_row.referral_code ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$', format('bare %s', v_row);

  -- a deleted account keeps its row, with the tombstone
  perform public.delete_user_account(v_bare);
  select * into v_row from public.support_user_overview where user_id = v_bare;
  assert v_row.deleted_at is not null and v_row.email = 'deleted+' || v_bare::text || '@invalid'
     and v_row.balance = 0, format('tombstone %s', v_row);
end;
$$;

-- privileges: service_role only
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000d101';
  v_count integer;
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', v_user::text, true);
  begin
    perform count(*) from public.support_user_overview;
    raise exception 'support_user_overview readable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
  execute 'set local role anon';
  begin
    perform count(*) from public.support_user_overview;
    raise exception 'support_user_overview readable by anon';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
  execute 'set local role service_role';
  select count(*) into v_count from public.support_user_overview where user_id = v_user;
  assert v_count = 1, 'service_role cannot read the view';
  execute 'reset role';
end;
$$;
