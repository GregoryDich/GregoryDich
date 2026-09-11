-- API keys (contract §11): create_api_key returns the plaintext once and stores only its
-- sha256; authenticate_api_key resolves the owner and stamps last_used_at; revoke_api_key
-- is owner-scoped and idempotent.
\set ON_ERROR_STOP on

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000a001';
  v_other uuid := '00000000-0000-4000-8000-00000000a002';
  v_key record;
  v_key2 record;
  v_hash text;
  v_row public.api_keys;
  v_revoked_at timestamptz;
begin
  insert into auth.users (id, email) values (v_user, 'keys@test.local'), (v_other, 'keys-other@test.local');

  select * into v_key from public.create_api_key(v_user, 'ci');
  assert v_key.plaintext ~ '^tm_live_[0-9a-f]{32}$', format('plaintext shape %s', v_key.plaintext);
  assert v_key.prefix = left(v_key.plaintext, 12), 'prefix';
  v_hash := encode(sha256(convert_to(v_key.plaintext, 'UTF8')), 'hex');
  select * into v_row from public.api_keys where id = v_key.id;
  assert found and v_row.user_id = v_user and v_row.key_hash = v_hash and v_row.prefix = v_key.prefix
     and v_row.name = 'ci' and v_row.revoked_at is null and v_row.last_used_at is null, 'stored key row';
  assert position(v_key.plaintext in v_row::text) = 0, 'plaintext was persisted';

  assert public.authenticate_api_key(v_hash) = v_user, 'authenticate by hash';
  assert (select last_used_at from public.api_keys where id = v_key.id) is not null, 'last_used_at not stamped';
  assert public.authenticate_api_key('deadbeef') is null, 'unknown hash authenticated';
  assert public.authenticate_api_key(v_key.plaintext) is null, 'plaintext authenticated';

  select * into v_key2 from public.create_api_key(v_user, null);
  assert v_key2.plaintext <> v_key.plaintext and v_key2.id <> v_key.id, 'keys are not unique';
  assert (select count(*) from public.api_keys where user_id = v_user) = 2, 'key count';

  -- revoke: owner-scoped, idempotent, effective immediately
  assert public.revoke_api_key(v_key.id, v_other) = false, 'revoke by another user succeeded';
  assert public.authenticate_api_key(v_hash) = v_user, 'foreign revoke took effect';
  assert public.revoke_api_key(v_key.id, v_user) = true, 'revoke by owner failed';
  select revoked_at into v_revoked_at from public.api_keys where id = v_key.id;
  assert v_revoked_at is not null, 'revoked_at not set';
  assert public.authenticate_api_key(v_hash) is null, 'revoked key still authenticates';
  assert public.revoke_api_key(v_key.id, v_user) = true, 'replayed revoke failed';
  assert (select revoked_at from public.api_keys where id = v_key.id) = v_revoked_at, 'replayed revoke moved revoked_at';
  assert public.revoke_api_key(gen_random_uuid(), v_user) = false, 'revoke of unknown key succeeded';
  assert public.authenticate_api_key(encode(sha256(convert_to(v_key2.plaintext, 'UTF8')), 'hex')) = v_user,
    'second key affected by revoking the first';

  begin
    perform public.create_api_key(gen_random_uuid(), null);
    raise exception 'key for an unknown user created';
  exception when sqlstate 'P0404' then null;
  end;
end;
$$;
