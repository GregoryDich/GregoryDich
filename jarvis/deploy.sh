#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_PATH="${JARVIS_DB:-$HOME/jarvis/state.db}"

echo "=== Jarvis Deploy ==="
echo ""

# --- 1. Collect credentials ---
read -rp "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
read -rp "Your Telegram Chat ID: " CHAT_ID
read -rp "n8n API URL (e.g. http://localhost:5678): " N8N_URL
read -rp "n8n API Key: " N8N_API_KEY

N8N_URL="${N8N_URL%/}"

echo ""
echo "[1/5] Creating state.db..."
bash "$SCRIPT_DIR/scripts/init_db.sh"

# Store chat_id in config
sqlite3 "$DB_PATH" "UPDATE config SET value='$CHAT_ID', updated_at=datetime('now') WHERE key='telegram_chat_id';"
echo "  → chat_id saved to config"

# --- 2. Set n8n environment variable ---
echo ""
echo "[2/5] Setting TELEGRAM_BOT_TOKEN in n8n..."
# Try to set env var via n8n API (works in n8n >= 1.22)
ENV_PAYLOAD="{\"name\":\"TELEGRAM_BOT_TOKEN\",\"value\":\"$TELEGRAM_BOT_TOKEN\"}"
ENV_RESP=$(curl -sf -X POST "$N8N_URL/api/v1/variables" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$ENV_PAYLOAD" 2>/dev/null || true)

if [ -z "$ENV_RESP" ]; then
  echo "  ⚠ Could not set via API. Add TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN to n8n environment manually."
else
  echo "  → TELEGRAM_BOT_TOKEN set in n8n variables"
fi

# --- 3. Import workflows ---
echo ""
echo "[3/5] Importing workflows..."

import_workflow() {
  local file="$1"
  local name
  name=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['name'])" "$file" 2>/dev/null || basename "$file" .json)

  RESP=$(curl -sf -X POST "$N8N_URL/api/v1/workflows" \
    -H "X-N8N-API-KEY: $N8N_API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$file" 2>/dev/null || true)

  if echo "$RESP" | grep -q '"id"'; then
    WF_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "?")
    echo "  → $name (id: $WF_ID)"

    # Activate
    curl -sf -X PATCH "$N8N_URL/api/v1/workflows/$WF_ID" \
      -H "X-N8N-API-KEY: $N8N_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"active": true}' > /dev/null 2>&1 || true
  else
    echo "  ✗ Failed to import $name"
    echo "    Try importing manually: n8n UI → Import from File → $file"
  fi
}

for wf in "$SCRIPT_DIR/workflows/"*.json; do
  import_workflow "$wf"
done

# --- 4. Set Telegram webhook ---
echo ""
echo "[4/5] Setting Telegram webhook..."
WEBHOOK_URL="$N8N_URL/webhook/jarvis-telegram"
WH_RESP=$(curl -sf "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$WEBHOOK_URL" 2>/dev/null || true)
if echo "$WH_RESP" | grep -q '"ok":true'; then
  echo "  → Webhook set to $WEBHOOK_URL"
else
  echo "  ⚠ Failed to set webhook. Ensure $WEBHOOK_URL is publicly accessible."
  echo "    If using localhost, run: ngrok http 5678"
  echo "    Then: curl 'https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=https://YOUR_NGROK/webhook/jarvis-telegram'"
fi

# --- 5. Test ---
echo ""
echo "[5/5] Testing..."

# Test notify
NOTIFY_RESP=$(curl -sf -X POST "$N8N_URL/webhook/jarvis-notify" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"$CHAT_ID\",\"text\":\"✅ Jarvis deployed successfully!\"}" 2>/dev/null || true)

if echo "$NOTIFY_RESP" | grep -q '"ok":true'; then
  echo "  → Test notification sent to Telegram!"
else
  echo "  ⚠ Notification test failed. Check workflow activation and token."
fi

echo ""
echo "=== Done ==="
echo "Commands: /ping, /status, /help"
echo "Notify webhook: POST $N8N_URL/webhook/jarvis-notify {chat_id, text}"
echo "Database: $DB_PATH"
