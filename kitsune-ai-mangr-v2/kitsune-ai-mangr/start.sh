#!/usr/bin/env bash
# ============================================================
# kitsune//ai-mangr - control the local ai chat server
#
#   bash start.sh          -> start (or restart) the web app
#   bash start.sh warm     -> start it + load model into RAM now
#   bash start.sh warm m   -> same, but force a specific model
#   bash start.sh stop     -> stop it
#   bash start.sh status   -> running? ollama up? model in RAM?
#
# one address, always: the app claims port 8788 and KEEPS it. a stale
# copy of this app is stopped automatically; if some OTHER program owns
# the port, start fails loudly instead of quietly moving to a new port
# (a moving address breaks phone home-screen bookmarks - that's the
# whole point of the fixed port).
#
# phone on the same wifi: the printed http://<lan-ip>:8788 is your one
# address - open it once, "add to home screen", done.
# away from home: bash tunnel.sh (temporary https url + QR).
# ============================================================
DIR="$(cd "$(dirname "$0")" && pwd)"
PID="$DIR/.server.pid"
LOG="$DIR/server.log"
PORT="${PORT:-8788}"
BIND="${BIND:-0.0.0.0}"
OLLAMA="http://127.0.0.1:11434"

is_up() { [ -f "$PID" ] && kill -0 "$(cat "$PID")" 2>/dev/null; }

stop_server() {
  if is_up; then
    kill "$(cat "$PID")" 2>/dev/null
    rm -f "$PID"
    echo "[ai-mangr] stopped"
  else
    rm -f "$PID"
    echo "[ai-mangr] was not running"
  fi
}

# pid listening on $PORT, empty if none (ss on debian, lsof/fuser as fallbacks)
port_pid() {
  local p
  p="$(ss -ltnp 2>/dev/null | grep "[:.]$PORT[[:space:]]" | grep -o 'pid=[0-9]*' | head -n1 | cut -d= -f2)"
  [ -z "$p" ] && p="$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -n1)"
  [ -z "$p" ] && p="$(fuser -n tcp "$PORT" 2>/dev/null | awk '{print $1}')"
  echo "$p"
}

# is the process on the port actually THIS app? probe its health endpoint
# instead of guessing from cmdline (works even if it was started from an
# old, since-moved copy of this folder)
port_is_kitsune() {
  local p="$1"
  curl -s --max-time 2 "http://127.0.0.1:$PORT/api/health" 2>/dev/null \
    | grep -q '"app":"kitsune//ai-mangr"'
}

# a stale copy of this app holding the port gets stopped (it would
# otherwise answer on the old code forever). anything else keeps the
# port - and the start below fails loudly rather than moving addresses.
free_port() {
  local p i
  p="$(port_pid)"
  [ -n "$p" ] || return 0
  if port_is_kitsune "$p"; then
    echo "[ai-mangr] a copy of this app is already on port $PORT (pid $p) - stopping it"
    kill "$p" 2>/dev/null
    for i in 1 2 3 4 5 6; do kill -0 "$p" 2>/dev/null || return 0; sleep 0.5; done
    kill -9 "$p" 2>/dev/null; sleep 0.5
  else
    echo "[ai-mangr] port $PORT is held by another program (pid $p) - not touching it"
  fi
}

lan_urls() {
  # best-effort LAN addresses for the phone (ipv4, private ranges)
  local ips=""
  if command -v hostname >/dev/null 2>&1; then
    ips="$(hostname -I 2>/dev/null)"
  fi
  [ -z "$ips" ] && ips="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | tr '\n' ' ')"
  for ip in $ips; do
    case "$ip" in
      10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*)
        echo "http://$ip:$PORT" ;;
    esac
  done
}

start_server() {
  if is_up; then
    echo "[ai-mangr] already running (pid $(cat "$PID")) - restarting"
    stop_server
  fi
  free_port
  rm -f "$DIR/.port"   # stale port from a previous run must not fool us
  BIND="$BIND" PORT="$PORT" nohup python3 "$DIR/server.py" >> "$LOG" 2>&1 &
  NEWPID=$!
  echo $NEWPID > "$PID"
  # the server writes .port with the port it actually bound - wait for it,
  # then health check it. if the port was stolen the server refuses to
  # start (by design) and says so.
  ACT=""
  for i in $(seq 1 10); do
    kill -0 "$NEWPID" 2>/dev/null || break
    ACT="$(cat "$DIR/.port" 2>/dev/null | tr -cd '0-9')"
    [ -n "$ACT" ] && curl -s --max-time 2 "http://127.0.0.1:$ACT/api/health" 2>/dev/null | grep -q '"ok":true' && break
    ACT=""
    sleep 1
  done
  if [ -z "$ACT" ]; then
    if kill -0 "$NEWPID" 2>/dev/null; then
      kill "$NEWPID" 2>/dev/null; rm -f "$PID"
    fi
    echo "[ai-mangr] FAILED to start - last log lines:"
    tail -n 6 "$LOG"
    exit 1
  fi
  echo "[ai-mangr] running (pid $(cat "$PID"))"
  echo "[ai-mangr] on this pc : http://localhost:$ACT"
  FIRST=1
  for u in $(lan_urls); do
    [ $FIRST -eq 1 ] && { echo "[ai-mangr] from phone : $u   <- one address, always (same wifi)"; FIRST=0; } \
                      || echo "[ai-mangr]              $u"
  done
  if [ $FIRST -eq 1 ]; then
    echo "[ai-mangr] from phone : (no LAN ip found - connect to the network and restart)"
  fi
  echo "[ai-mangr] phone setup: open the url there -> share -> add to home screen"
  echo "[ai-mangr] the tap of the phone button in the app shows these + a QR code"
  echo "[ai-mangr] model     : loads on first message (30-60s) - or: bash start.sh warm"
  echo "[ai-mangr] logs      : tail -f $LOG"
}

status_server() {
  if is_up; then
    A="$(cat "$DIR/.port" 2>/dev/null | tr -cd '0-9')"
    A="${A:-$PORT}"
    echo "[ai-mangr] running (pid $(cat "$PID")) on http://localhost:$A"
    for u in $(lan_urls); do echo "[ai-mangr] from phone : $u"; done
    if curl -s --max-time 4 "http://127.0.0.1:$A/api/health" | grep -q '"ollama":true'; then
      echo "[ai-mangr] ollama: reachable"
      INRAM=$(curl -s --max-time 4 "$OLLAMA/api/ps" 2>/dev/null \
        | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | paste -sd, -)
      echo "[ai-mangr] model in RAM: ${INRAM:-none (loads on first message)}"
    else
      echo "[ai-mangr] ollama: NOT reachable (start it: ollama serve)"
    fi
  else
    echo "[ai-mangr] not running"
  fi
}

warm_model() {
  # default model = first 'model:' or 'model =' line in bots/*.ai, else dolphin3:8b
  DEFM="$(grep -h '^model[[:space:]]*[=:]' "$DIR"/bots/*.ai 2>/dev/null | head -n1 \
        | sed 's/^model[[:space:]]*[=:][[:space:]]*//' | tr -d '"\r')"
  M="${1:-$DEFM}"
  [ -n "$M" ] || M="dolphin3:8b"
  curl -s --max-time 5 "$OLLAMA/api/tags" >/dev/null 2>&1 \
    || { echo "[ai-mangr] ollama not reachable - start it: ollama serve"; exit 1; }
  echo "[ai-mangr] warming $M into RAM (30-60s first time)..."
  R=$(curl -s --max-time 300 "$OLLAMA/api/generate" \
        -d "{\"model\":\"$M\",\"keep_alive\":-1}")
  if echo "$R" | grep -q '"error"'; then
    echo "[ai-mangr] warm failed: $(echo "$R" | head -c 200)"
    echo "[ai-mangr] fix with: ollama pull $M"
    exit 1
  fi
  if curl -s --max-time 5 "$OLLAMA/api/ps" | grep -q "\"name\":\"$M"; then
    echo "[ai-mangr] $M is in RAM - stays there until you stop it"
  else
    echo "[ai-mangr] warm request sent (verify with: bash start.sh status)"
  fi
}

case "$1" in
  ""|start|restart) start_server ;;
  warm)             is_up || start_server; warm_model "$2" ;;
  stop)             stop_server ;;
  status)           status_server ;;
  *) echo "usage: bash start.sh [start|stop|status|warm [model]]" ;;
esac
