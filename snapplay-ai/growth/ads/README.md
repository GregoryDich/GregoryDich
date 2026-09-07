# Paid amplification (stub)

Turn the best-performing organic shorts into Meta ad creatives through the Marketing API.
This directory documents the scope; nothing here is wired into the MCP server yet.

## Scope

1. **Select winners.** `report_metrics` stores per-post views / likes / CTR on each content
   item. A selector picks items whose Instagram or Facebook post beats a threshold (e.g. top
   20 % by `ctr` over the last 7 days, minimum 1 000 views).
2. **Upload the creative.** `POST /{ad_account_id}/advideos` with the rendered mp4 (the same
   file `render_video` produced) and a thumbnail from frame 15.
3. **Create the ad creative.** `POST /{ad_account_id}/adcreatives` with
   `object_story_spec.video_data` (`video_id`, `message` = the organic caption, `call_to_action`
   `LEARN_MORE` → the SnapPlay landing page carrying `utm_content=<content_item_id>`), or
   `source_instagram_media_id` to boost the existing Reel and keep its social proof.
4. **Campaign structure.** One evergreen campaign (`OUTCOME_TRAFFIC` or `OUTCOME_APP_PROMOTION`),
   one ad set per angle (`speed`, `bass`, `sample_flip`, `tutorial`) so budgets can follow the
   winning angle, one ad per content item. Ads start `PAUSED`; a human flips them on.
5. **Feedback loop.** Read `insights` (spend, CPC, CTR, conversions) back onto the content
   item so the next batch favours the angles that convert.

## Prerequisites

* A Meta Business Manager with an ad account, a Facebook Page and a linked Instagram
  professional account; the system-user token needs `ads_management`, `ads_read`,
  `business_management`, `pages_read_engagement` and `instagram_basic`.
* Advertising rights for every clip used (see the rights notice in `../README.md`); music in
  paid ads is checked by Meta's rights manager and unlicensed audio is rejected or muted.
* A conversion pixel / app event for the free-credits sign-up so optimisation targets the
  right outcome.

## Configuration to add when wiring it up

`META_AD_ACCOUNT_ID`, `META_ADS_ACCESS_TOKEN`, `ADS_LANDING_URL`, `ADS_DAILY_BUDGET_CENTS`,
`ADS_MIN_VIEWS`, `ADS_TOP_PERCENT`.
