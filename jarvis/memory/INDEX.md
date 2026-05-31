# Jarvis Knowledge Index

## Projects
| Slug | Name | Status | Notes |
|------|------|--------|-------|
| fitscan | FitScan | active | Body scanning app. Shopify storefront + backend. |

## Systems
| System | Location | Purpose |
|--------|----------|---------|
| n8n | localhost:5678 (Docker) | Workflow automation engine |
| state.db | ~/jarvis/state.db | Central state: tasks, events, metrics |
| Telegram Bot | @YourJarvisBot | Command interface + notifications |
| Shopify | fitscan store | E-commerce frontend |
| GitHub Actions | GregoryDich repos | CI/CD pipelines |

## Workflows
| Name | File | Trigger | Purpose |
|------|------|---------|---------|
| Jarvis Telegram Bot | jarvis_telegram.json | Webhook (Telegram) | Handle /ping, /status, /help |
| Jarvis Notify | jarvis_notify.json | Webhook (internal) | Send outbound Telegram messages |
| FitScan Collector | fitscan_collector.json | Cron 15min | Gather FitScan health metrics |

## Metrics Tracked (fitscan_state)
- `ci_tests` — last GitHub Actions run result
- `deploy_health` — HTTP check on deploy URL
- `shopify_store` — Shopify storefront accessibility

## Config Keys
- `telegram_chat_id` — owner's Telegram chat ID
- `n8n_base_url` — n8n instance URL
- `fitscan_github_repo` — GitHub repo (owner/repo format)
- `fitscan_deploy_url` — Production health-check URL
- `fitscan_shopify_store` — Shopify store subdomain
- `collector_interval_min` — FitScan check interval
