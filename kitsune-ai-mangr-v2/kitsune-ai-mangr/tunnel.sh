#!/usr/bin/env bash
# ============================================================
# kitsune//ai-mangr - tunnel.sh: reach the app from OUTSIDE your wifi
#
#   bash tunnel.sh     -> cloudflared quick tunnel to the app's port,
#                         prints URL + QR code
#
# at home you don't need this at all - the app prints its LAN address
# (also shown in the app: the phone button). the tunnel is for when you
# are out and about: the URL is random and dies when the tunnel stops or
# the laptop sleeps. rerun, rescan, done.
#
# the port is read from .port (written by the server at boot - 8788).
# an explicit PORT=... still wins.
# ============================================================
DIR="$(cd "$(dirname "$0")" && pwd)"
# which port is the chat server on? an explicit PORT wins; otherwise read
# the .port file the server writes at boot (8788 - it stays fixed now)
PORT="${PORT:-}"
if [ -z "$PORT" ] && [ -f "$DIR/.port" ]; then
  P="$(tr -cd '0-9' < "$DIR/.port" 2>/dev/null)"
  [ -n "$P" ] && PORT="$P"
fi
PORT="${PORT:-8788}"
LOG="$DIR/.tunnel.log"
PID="$DIR/.tunnel.pid"

command -v cloudflared >/dev/null \
  || { echo "[ai-mangr] cloudflared not installed"; exit 1; }

curl -s --max-time 3 "http://127.0.0.1:$PORT/api/health" 2>/dev/null | grep -q '"ok":true' \
  || echo "[ai-mangr] note: nothing answering on port $PORT (bash start.sh first?)"

# reuse existing tunnel if alive
if [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  U=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -n1)
  [ -n "$U" ] && { echo "[ai-mangr] tunnel already up: $U"; QR="$U"; show=1; }
fi

if [ -z "$show" ]; then
  : > "$LOG"
  nohup cloudflared tunnel --url "http://127.0.0.1:$PORT" --protocol http2 > "$LOG" 2>&1 &
  echo $! > "$PID"
  echo "[ai-mangr] starting tunnel..."
  U=""
  for i in $(seq 1 20); do
    U=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -n1)
    [ -n "$U" ] && break
    sleep 1
  done
  [ -n "$U" ] || { echo "[ai-mangr] tunnel gave no URL - check $LOG"; exit 1; }
  QR="$U"
fi

echo "[ai-mangr] open this on your phone: $QR"
if command -v qrencode >/dev/null 2>&1; then
  echo
  qrencode -t ansiutf8 "$QR"
  echo
  echo "[ai-mangr] scan that with your phone camera -> opens your chat app"
else
  echo "[ai-mangr] tip: install qrencode, then rerun for a QR code"
fi
echo "[ai-mangr] stop the tunnel: kill \$(cat $PID)"
