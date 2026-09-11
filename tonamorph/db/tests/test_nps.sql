-- NPS answers (contract §14): one per user per 30 days, validated, scoped.
\set ON_ERROR_STOP on

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009201';
  v_row public.nps_responses;
  v_first uuid;
begin
  insert into auth.users (id, email) values (v_user, 'nps-answers@test.local');

  v_row := public.submit_nps(v_user, 10, 'fast and in key');
  assert v_row.user_id = v_user and v_row.score = 10 and v_row.comment = 'fast and in key'
     and v_row.created_at <= now(), 'first answer';
  v_first := v_row.id;

  begin
    perform public.submit_nps(v_user, 2, null);
    raise exception 'a second answer inside 30 days was accepted';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;
  assert (select count(*) from public.nps_responses where user_id = v_user) = 1, 'row count after refusal';

  update public.nps_responses set created_at = now() - interval '31 days' where id = v_first;
  v_row := public.submit_nps(v_user, 7, null);
  assert v_row.score = 7 and v_row.comment is null, 'answer after the cooldown';
  assert (select count(*) from public.nps_responses where user_id = v_user) = 2, 'two answers';

  begin
    perform public.submit_nps(v_user, 11, null);
    raise exception 'score 11 accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.submit_nps(v_user, -1, null);
    raise exception 'score -1 accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.submit_nps(v_user, 5, repeat('c', 501));
    raise exception 'long comment accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.submit_nps(gen_random_uuid(), 5, null);
    raise exception 'unknown profile accepted';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;
end;
$$;
