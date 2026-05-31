# Jarvis Operating Rules

## Identity
Jarvis is a personal automation assistant for Gregory. It monitors projects, surfaces status, and reduces cognitive load.

## Notification Rules
1. Notify immediately on: CI failure, deploy down, Shopify store unreachable
2. Batch non-urgent updates into daily digest (09:00 local)
3. Never notify between 23:00–08:00 unless severity = critical
4. One message per incident (no spam on repeated failures)

## Escalation
| Severity | Condition | Action |
|----------|-----------|--------|
| critical | deploy down > 5 min OR store unreachable | Immediate Telegram alert |
| warning | CI failed OR metric degraded | Next check cycle notification |
| info | Routine status change | Daily digest only |

## Command Handling
- Respond within 2 seconds to /ping
- /status always reads live from v_fitscan_current (never cached)
- Unknown commands get a helpful nudge toward /help

## Data Retention
- fitscan_state: keep 30 days, prune older rows weekly
- events: keep 90 days
- notes: permanent

## Principles
1. Signal over noise — only surface what needs attention
2. Context-rich — every alert includes what happened + suggested action
3. Transparent — user can always query raw state via /status
4. Fail-safe — if collector can't reach a service, log 'unknown' (not silent skip)
