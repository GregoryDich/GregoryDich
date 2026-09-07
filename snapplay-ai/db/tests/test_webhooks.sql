-- Webhook delivery claims (contract §4): an event is applied at most once, a delivery that
-- failed halfway is retryable, and a claim whose holder was killed mid-apply is taken over
-- once its lease has run out instead of stranding a paid event forever.
\set ON_ERROR_STOP on

do $$
declare
  v_key text := 'lemonsqueezy:order_created:evt-1';
  v_lease integer := 300;
  v_row public.webhook_events;
  v_received timestamptz;
begin
  -- A new event is claimed, and the row records the delivery.
  assert public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created',
                                    '{"meta":{"event_name":"order_created"}}'::jsonb, v_lease),
    'a new event was not claimed';
  select * into v_row from public.webhook_events where idempotency_key = v_key;
  assert found and v_row.provider = 'lemonsqueezy' and v_row.event_name = 'order_created'
     and v_row.payload -> 'meta' ->> 'event_name' = 'order_created'
     and v_row.processed_at is null and v_row.error is null, 'claim did not store the delivery';

  -- A second delivery of the same event while the first is still being applied is a
  -- duplicate: the claim is inside its lease.
  assert not public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'a claim inside its lease was handed out twice';

  -- Applied cleanly: every later delivery is a duplicate, however old the row gets.
  update public.webhook_events set processed_at = now(), error = null where idempotency_key = v_key;
  assert not public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'a processed event was claimed again';
  update public.webhook_events set received_at = now() - interval '30 days',
                                   processed_at = now() - interval '30 days'
   where idempotency_key = v_key;
  assert not public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'an old processed event was claimed again';

  -- Applied with an error: the provider's retry has to run it, whatever its age.
  update public.webhook_events set processed_at = now(), error = 'internal_error'
   where idempotency_key = v_key;
  assert public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'a failed delivery was answered duplicate instead of being retried';

  -- Killed mid-apply: the claim was never closed either way. Inside the lease it stands,
  -- past it the next retry takes it over and starts a fresh lease.
  update public.webhook_events set processed_at = null, error = null, received_at = now()
   where idempotency_key = v_key;
  assert not public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'a fresh unfinished claim was stolen';
  update public.webhook_events set received_at = now() - make_interval(secs => v_lease + 1)
   where idempotency_key = v_key;
  assert public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'a stranded claim past its lease was not reclaimed';
  select received_at into v_received from public.webhook_events where idempotency_key = v_key;
  assert v_received > now() - interval '1 second', 'the reclaim did not restart the lease';
  assert not public.claim_webhook_event(v_key, 'lemonsqueezy', 'order_created', '{}'::jsonb, v_lease),
    'the reclaimed event was handed out a second time';

  -- Arguments are validated: an empty key or a non-positive lease is a caller bug, not a
  -- reason to hand the same paid event to two workers.
  begin
    perform public.claim_webhook_event('', 'paddle', 'transaction.completed', '{}'::jsonb, v_lease);
    raise exception 'empty idempotency key was accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.claim_webhook_event('k2', 'paddle', 'transaction.completed', '{}'::jsonb, 0);
    raise exception 'a zero lease was accepted';
  exception when sqlstate '22023' then null;
  end;
  assert (select count(*) from public.webhook_events where idempotency_key in ('', 'k2')) = 0,
    'a rejected claim inserted a row';

  delete from public.webhook_events where idempotency_key = v_key;
end;
$$;
