#!/usr/bin/env python3
# ============================================================
# kitsune//ai-mangr v2 - your own local AI chat manager, powered by Ollama
#
#   bots  = plain .ai text files in  bots/   (edit in vim, live reload)
#   chats = json files in           chats/
#   ui    = index.html - right next to this file
#   config/theme.conf + config/settings.conf = looks + app switches
#
# run:   bash start.sh                (or: python3 server.py)
# port:  8788 - and it STAYS 8788. one address, always. if the port is
#        genuinely taken the server refuses to start with a clear message
#        instead of quietly hopping to another port (that silently broke
#        phone bookmarks - no more).
# bind:  0.0.0.0 so your phone on the same wifi reaches it. lock it back
#        down to this pc only with:  BIND=127.0.0.1 python3 server.py
# ollama: http://localhost:11434  (env OLLAMA_URL to change)
#
# away from home? bash tunnel.sh gives you a temporary https url + QR.
# at home the LAN address above IS your one address - put it on your
# phone's home screen once and never type it again.
# ============================================================

import base64
import json
import os
import re
import shutil
import signal
import socket
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "2.0"

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE, "config")            # theme.conf + settings.conf live here
BOTS_DIR = os.path.join(BASE, "bots")
CHATS_DIR = os.path.join(BASE, "chats")
AVATARS_DIR = os.path.join(BASE, "avatars")          # home for bot profile pics

def migrate_configs():
    """older installs kept theme.conf / settings.conf next to server.py -
    tuck them into config/ on boot so the folder is the single home."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        for fn in ("theme.conf", "settings.conf"):
            old = os.path.join(BASE, fn)
            new = os.path.join(CONFIG_DIR, fn)
            if os.path.isfile(old) and not os.path.isfile(new):
                os.replace(old, new)
    except Exception:
        pass   # a failed migration must never keep the server from booting

DEFAULT_AVATAR = os.path.join(BASE, "avatar.png")   # the default profile png

# where the ui can live, first match wins. index.html sitting next to
# server.py is the normal case; the rest cover odd unzip layouts.
INDEX_CANDIDATES = [
    os.path.join(BASE, "index.html"),
    os.path.join(BASE, "web", "index.html"),
    os.path.join(BASE, "ai-server", "index.html"),
    os.path.join(BASE, "ai-server", "web", "index.html"),
]

# minimal service worker: just enough for "add to home screen" install.
# passthrough fetch - everything hits the local server anyway.
SW_SOURCE = (
    "self.addEventListener('install',e=>self.skipWaiting());"
    "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"
    "self.addEventListener('fetch',e=>{});"
)

PORT = int(os.environ.get("PORT", "8788"))
HOST = os.environ.get("BIND", "0.0.0.0")   # 0.0.0.0 = LAN visible; 127.0.0.1 = this pc only
PORT_FILE = os.path.join(BASE, ".port")    # the port actually bound (read by tunnel.sh)
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "dolphin3:8b")

# ------------------------------------------------------------
# .ai file format  (bots/<name>.ai - plain text, edit anytime)
#
#   name: "Aria"
#   description: "who they are, how they talk - the system prompt"
#   greeting: "their first message"
#
#   color: "#d4a373"      (optional, list dot color)
#   model: "dolphin3:8b"  (optional, else pick per chat in the ui)
#
#   temperature: "0.9"    (optional, creativity 0-2, default ollama)
#   max_tokens: "400"     (optional, reply length cap)
#
#   icon: "avatars/x.png" (optional profile pic - the bot creator in
#                          the ui writes this one. avatar: still works
#                          as the older alias; last one in the file wins)
#
# values may be quoted or bare. any line that is not "key: value"
# continues the field above it, so multi-line descriptions and
# greetings just work. blank lines separate fields visually and
# are ignored. lines starting with '#' BEFORE the first field
# are comments.
# ------------------------------------------------------------

FIELDS = ("name", "description", "greeting", "color", "model", "tagline",
          "temperature", "max_tokens", "avatar", "icon")

def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    return v

def parse_ai(path):
    bot = {"file": os.path.basename(path), "name": "", "description": "",
           "greeting": "", "color": "#ff9042", "model": "",
           "temperature": "", "max_tokens": "", "avatar": ""}
    cur = None
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"^(\w+)\s*:\s*(.*)$", line.strip())
            if m and m.group(1).lower() in FIELDS:
                cur = m.group(1).lower()
                if cur == "icon":
                    cur = "avatar"   # icon: is the new name for avatar:
                if cur in bot:
                    bot[cur] = unquote(m.group(2))
                continue
            if line.strip().startswith("#") and cur is None:
                continue                     # comment before the first field
            if cur and cur in bot:
                bot[cur] = (bot[cur] + "\n" + line.strip()).strip()
    if not bot["name"]:
        bot["name"] = os.path.splitext(os.path.basename(path))[0].replace("-", " ").title()
    return bot

def slug(s):
    s = re.sub(r"[^a-z0-9-_]+", "-", str(s).lower()).strip("-")
    return s or "bot"

def bot_path(name):
    return os.path.join(BOTS_DIR, slug(name) + ".ai")

def find_bot_file(name):
    """path of the .ai file whose slug matches name, or None. exact slug
    file first, then a scan - so files you drop in by hand (Aria.ai,
    'my bot.ai') resolve even though the api only ever uses slugs."""
    s = slug(name)
    p = os.path.join(BOTS_DIR, s + ".ai")
    if os.path.isfile(p):
        return p
    if os.path.isdir(BOTS_DIR):
        for fn in sorted(os.listdir(BOTS_DIR)):
            if fn.lower().endswith(".ai") and slug(fn[:-3]) == s:
                return os.path.join(BOTS_DIR, fn)
    return None

def load_bot(name):
    p = find_bot_file(name)
    return parse_ai(p) if p else None

IMG_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp"}

def resolve_avatar(v):
    """avatar:/icon: value -> safe absolute path, or None. accepts a bare
    filename (looked up next to server.py and in avatars/) or an explicit
    "avatars/<file>" path - never folders above that, never .."""
    v = (v or "").strip().strip("\"'")
    if not v or ".." in v:
        return None
    m = re.match(r"^avatars[/\\]([\w][\w .()-]*\.(?:png|jpe?g|gif|webp))$", v, re.I)
    if m:
        p = os.path.join(AVATARS_DIR, m.group(1))
        return p if os.path.isfile(p) else None
    if re.search(r"[\\/]+", v):
        return None
    for d in (BASE, AVATARS_DIR):
        p = os.path.join(d, v)
        if os.path.isfile(p):
            return p
    return None

def avatar_mime(path):
    return IMG_MIME.get(os.path.splitext(path)[1].lower(), "image/png")

def save_data_image(dataurl, base_name):
    """icon picked in the ui ("data:image/...;base64,...") -> saved as
    avatars/<base>-icon.<ext>. returns "avatars/<file>" for the .ai file,
    or "" if there was nothing usable."""
    if not dataurl:
        return ""
    m = re.match(r"^data:image/(png|jpe?g|gif|webp);base64,(.+)$",
                 str(dataurl).strip(), re.S)
    if not m:
        return ""
    ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
    try:
        raw = base64.b64decode(m.group(2))
    except Exception:
        return ""
    if not raw or len(raw) > 4 * 1024 * 1024:
        return ""
    os.makedirs(AVATARS_DIR, exist_ok=True)
    fn = "%s-icon.%s" % (base_name, ext)
    for old in os.listdir(AVATARS_DIR):   # drop an older -icon.* with a different ext
        if old.startswith("%s-icon." % base_name) and old != fn:
            try: os.remove(os.path.join(AVATARS_DIR, old))
            except OSError: pass
    with open(os.path.join(AVATARS_DIR, fn), "wb") as f:
        f.write(raw)
    return "avatars/" + fn

def list_bots():
    if not os.path.isdir(BOTS_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(BOTS_DIR)):
        if fn.lower().endswith(".ai"):
            try:
                b = parse_ai(os.path.join(BOTS_DIR, fn))
                d = " ".join(b["description"].split())
                out.append({"name": b["name"], "file": fn, "id": slug(fn[:-3]),
                            "desc": d[:90] + ("..." if len(d) > 90 else ""),
                            "color": b["color"] or "#ff9042", "model": b["model"],
                            "avatar": "/api/bots/%s/avatar" % slug(fn[:-3])})
            except Exception as e:
                out.append({"name": fn, "file": fn, "id": slug(fn[:-3]),
                            "desc": "broken file: %s" % e,
                            "color": "#e06c75", "model": "",
                            "avatar": "/api/bots/%s/avatar" % slug(fn[:-3])})
    return out

def _num_or_empty(v, cast):
    """temperature/max_tokens typed from the manager menu - keep valid
    numbers, silently drop anything a hand-edit or typo left behind"""
    v = str(v or "").strip()
    if not v:
        return ""
    try:
        return str(cast(v))
    except Exception:
        return ""

def write_ai_to(path, b, fallback_name):
    """emit the flat .ai format to an explicit path (create AND edit)"""
    out = []
    def emit(key, val):
        val = (val or "").strip()
        if "\n" in val:
            # multi-line value: bare lines under the key, no quotes
            out.append(key + ":")
            out.extend(val.split("\n"))
        else:
            out.append('%s: "%s"' % (key, val.replace('"', "'")))
    emit("name", b.get("name", fallback_name))
    emit("description", b.get("description", ""))
    emit("greeting", b.get("greeting", ""))
    out.append("")
    emit("color", b.get("color") or "#ff9042")
    if b.get("model"):
        emit("model", b["model"])
    temperature = _num_or_empty(b.get("temperature"), float)
    if temperature:
        emit("temperature", temperature)
    max_tokens = _num_or_empty(b.get("max_tokens"), int)
    if max_tokens:
        emit("max_tokens", max_tokens)
    if b.get("avatar"):
        emit("icon", b["avatar"])   # canonical key; avatar: still parses as an alias
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip() + "\n")

def write_ai(name, b):
    write_ai_to(bot_path(name), b, name)

# ------------------------------------------------------------
# chat storage:  chats/<bot-slug>/<chat-id>.json
# each file: {"id":..., "title":..., "model":..., "messages":[{"role","content"}...]}
# ------------------------------------------------------------

def chat_dir(bot_name):
    d = os.path.join(CHATS_DIR, slug(bot_name))
    os.makedirs(d, exist_ok=True)
    return d

def chat_file(bot_name, chat_id):
    if not re.match(r"^[0-9]+$", str(chat_id)):
        raise ValueError("bad chat id")
    return os.path.join(chat_dir(bot_name), "%s.json" % chat_id)

def load_chat(bot_name, chat_id):
    with open(chat_file(bot_name, chat_id), encoding="utf-8") as f:
        return json.load(f)

def save_chat(bot_name, data):
    path = chat_file(bot_name, data["id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

def list_chats(bot_name):
    d = os.path.join(CHATS_DIR, slug(bot_name))
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d), reverse=True):
        if fn.endswith(".json"):
            p = os.path.join(d, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    c = json.load(f)
                try: mt = int(os.path.getmtime(p))   # last activity, for the chats menu
                except Exception: mt = 0
                out.append({"id": c["id"], "title": c.get("title", "(empty)"),
                            "model": c.get("model", ""),
                            "turns": max(0, len(c.get("messages", [])) - 1),
                            "updated": mt})
            except Exception:
                pass
    return out

# sent to the model on /api/continue but never stored in the chat file
CONTINUE_NUDGE = ("Continue the scene exactly where it left off. Do not summarize, "
                  "do not repeat, do not start a new scene - just keep going naturally.")

def system_prompt(bot):
    p = "You are %s." % bot["name"]
    if bot.get("description"):
        p += "\n\n" + bot["description"]
    p += ("\n\nStay fully in character. Never mention being an AI or a language "
          "model. Put actions in *asterisks*. Keep replies conversational unless "
          "the scene calls for longer.")
    return p

# ------------------------------------------------------------
# theming: config/theme.conf, kitty-style
#   accent #ff0000        key value, one per line
#   # this is a comment
# ------------------------------------------------------------

THEME_KEYS = {
    "background": "--bg",
    "foreground": "--text",
    "accent": "--accent",
    "accent_text": "--accent-text",
    "danger": "--danger",
    "dim": "--dim",
    "line": "--line",
    "panel": "--panel",
    "panel2": "--panel2",
    "user_bubble": "--user-b",
    "scrollbar": "--scroll",
    "font": "--font",
    "font_size": "--font-size",
    "radius": "--radius",
}

def _safe_css(v):
    # theme.conf is the user's own file, but keep anything weird
    # (braces, semicolons, angle brackets) out of the css anyway
    v = v.strip().strip('"').strip("'")
    return v if re.fullmatch(r"[A-Za-z0-9_#.,%()\-+/ ']+", v) else None

THEME_FILE = os.path.join(CONFIG_DIR, "theme.conf")

def theme_map():
    """config/theme.conf parsed to {key: value}, unknown keys dropped"""
    m = {}
    if os.path.isfile(THEME_FILE):
        try:
            with open(THEME_FILE, encoding="utf-8-sig") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    line = re.sub(r"\s+#\s.*$", "", line)   # inline "  # comment"
                    parts = line.split(None, 1)
                    if len(parts) != 2:
                        continue
                    val = _safe_css(parts[1])
                    if val:
                        m[parts[0].lower()] = val
        except Exception:
            pass
    return m

def load_theme():
    """returns a <style> override block built from theme.conf, or ''"""
    t = theme_map()
    rules = ["%s:%s" % (var, t[key]) for key, var in THEME_KEYS.items() if t.get(key)]
    if not rules:
        return ""
    return "<style>:root{" + ";".join(rules) + "}</style>"

# ------------------------------------------------------------
# Ollama
# ------------------------------------------------------------

_ollama_state = {"ok": None, "t": 0.0}   # tiny cache so pre-flight checks stay cheap

def ollama_ok(max_age=3.0):
    if _ollama_state["ok"] is not None and time.time() - _ollama_state["t"] < max_age:
        return _ollama_state["ok"]
    ok = False
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=4) as r:
            ok = r.status == 200
    except Exception:
        ok = False
    _ollama_state["ok"] = ok
    _ollama_state["t"] = time.time()
    return ok

def ollama_models():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=4) as r:
            data = json.loads(r.read().decode())
        return [{"name": m.get("name", ""), "size": m.get("size", 0)} for m in data.get("models", [])]
    except Exception:
        return []

# can this model see pictures? ollama's /api/show lists model capabilities
# and vision models carry "vision" in there. None = ollama couldn't tell us
# (old ollama versions, model not pulled yet) - the ui then just shows the
# attach button anyway and lets ollama have the final say.
_vision_cache = {}   # model -> (time, True/False/None)

def model_can_see(model, ttl=120):
    if not model:
        return None
    now = time.time()
    hit = _vision_cache.get(model)
    if hit and now - hit[0] < ttl:
        return hit[1]
    see = None
    try:
        req = urllib.request.Request(
            OLLAMA + "/api/show",
            data=json.dumps({"model": model}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            caps = json.loads(r.read().decode()).get("capabilities") or []
        see = "vision" in caps
    except Exception:
        see = None
    _vision_cache[model] = (now, see)
    return see

# ------------------------------------------------------------
# settings.conf - app switches (kitty-style like theme.conf)
#
#   single_model on     before each reply, unload every other model
#                       sitting in ram - 8gb holds one at a time
#
# the ui's gear button writes this file; hand edits work the same.
# ------------------------------------------------------------
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.conf")

def settings_map():
    """settings.conf parsed to {key: value}; missing file = {}"""
    m = {}
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8-sig") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        m[parts[0].lower()] = parts[1].strip().strip("\"'")
        except Exception:
            pass
    return m

def single_model_enabled():
    v = str(settings_map().get("single_model", "on")).lower()
    return v not in ("off", "false", "0", "no", "disabled")

def set_single_model(on):
    """flip single_model in settings.conf, keep the user's other lines."""
    lines = []
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []
    out, hit = [], False
    for ln in lines:
        if re.match(r"^\s*single_model\b", ln):
            out.append("single_model " + ("on" if on else "off")); hit = True
        else:
            out.append(ln)
    if not hit:
        if out and out[-1].strip():
            out.append("")
        out.append("single_model " + ("on" if on else "off"))
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(out).rstrip() + "\n")
    except Exception:
        pass

def loaded_models():
    """ollama /api/ps -> names of models sitting in ram right now
    (tag forced on so 'dolphin3' and 'dolphin3:latest' compare equal).
    [] whenever ollama is silent - then we simply do nothing."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/ps", timeout=4) as r:
            data = json.loads(r.read().decode() or "{}")
        out = []
        for m in data.get("models") or []:
            n = (m.get("name") or "").strip()
            if n:
                out.append(n if ":" in n else n + ":latest")
        return out
    except Exception:
        return []

def unload_model(name):
    """the official way to drop a model from ram: a generate call with
    keep_alive 0. never raises - a failed unload must not break a chat."""
    try:
        req = urllib.request.Request(
            OLLAMA + "/api/generate",
            data=json.dumps({"model": name, "keep_alive": 0}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass

def enforce_single_model(keep):
    """one model in ram at a time (settings.conf, on by default): before a
    reply, every OTHER loaded model gets keep_alive:0 -> unloaded. the model
    about to talk is always left alone."""
    if not single_model_enabled():
        return
    keep = (keep or "").strip()
    if ":" not in keep:
        keep += ":latest"
    for name in loaded_models():
        if name != keep:
            unload_model(name)

# pictures in chat: the ui sends base64 (a data-uri prefix is tolerated),
# we validate, store them on the user message in the chat file and pass
# them straight to ollama. vision models see them; models we KNOW are
# blind get the images stripped out so ollama never chokes on them.
MAX_IMAGES = 4
MAX_IMG_BYTES = 8 * 1024 * 1024      # per decoded picture

def clean_images(imgs):
    """validate the images payload -> list of bare base64 strings.
    raises ValueError with a human-readable message on anything weird."""
    if imgs is None:
        return []
    if not isinstance(imgs, list):
        raise ValueError("images must be a list")
    if len(imgs) > MAX_IMAGES:
        raise ValueError("max %d pictures per message" % MAX_IMAGES)
    out = []
    for im in imgs:
        s = re.sub(r"\s+", "", str(im))
        s = re.sub(r"^data:[^,]*,", "", s)   # tolerate data:image/jpeg;base64,
        if not s:
            continue
        try:
            raw = base64.b64decode(s, validate=True)
        except Exception:
            raise ValueError("bad picture data (expected base64)")
        if len(raw) < 64:
            raise ValueError("picture data too small")
        if len(raw) > MAX_IMG_BYTES:
            raise ValueError("picture too big (8mb cap per picture)")
        out.append(s)
    return out

def bot_options(bot):
    """temperature / max_tokens from the .ai file -> ollama options"""
    opts = {}
    try:
        if bot.get("temperature"):
            opts["temperature"] = float(bot["temperature"])
    except (TypeError, ValueError):
        pass
    try:
        if bot.get("max_tokens"):
            opts["num_predict"] = int(float(bot["max_tokens"]))
    except (TypeError, ValueError):
        pass
    return opts

def ollama_chat_stream(model, messages, options=None):
    """yields content deltas from Ollama's native NDJSON chat stream"""
    body = {"model": model, "messages": messages, "stream": True, "keep_alive": -1}
    if options:
        body["options"] = options
    payload = json.dumps(body).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("error"):
                raise RuntimeError("Ollama: %s" % obj["error"])
            tok = obj.get("message", {}).get("content", "")
            if tok:
                yield tok
            if obj.get("done"):
                return

# ------------------------------------------------------------
# one address: LAN discovery - the phone needs to know where to point
# ------------------------------------------------------------

def _is_lan_ip(ip):
    if not ip or ip.startswith("127.") or ip.startswith("169.254."):
        return False
    if ip.startswith("10.") or ip.startswith("192.168."):
        return True
    m = re.match(r"^172\.(\d+)\.", ip)
    return bool(m and 16 <= int(m.group(1)) <= 31)

def lan_ips():
    """private ipv4 addresses of this machine, primary first. falls back
    to any non-loopback ipv4 when the network uses odd addressing - an
    approximate address beats an empty phone menu."""
    candidates = []
    try:   # the udp trick: no packet is actually sent
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip:
            candidates.append(ip)
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and ip not in candidates:
                candidates.append(ip)
    except Exception:
        pass
    ips = [ip for ip in candidates if _is_lan_ip(ip)]
    if not ips:   # odd network (public ranges, cgnat...) - show something
        ips = [ip for ip in candidates if ip and not ip.startswith("127.")][:1]
    return ips

def lan_info():
    """everything the ui's phone menu needs"""
    info = {"port": PORT, "bound": HOST, "ips": lan_ips(),
            "hostname": socket.gethostname().split(".")[0],
            "version": VERSION}
    info["urls"] = ["http://%s:%d" % (ip, PORT) for ip in info["ips"]]
    if HOST != "127.0.0.1" and info["hostname"]:
        info["local_url"] = "http://%s.local:%d" % (info["hostname"], PORT)
    else:
        info["local_url"] = ""
    return info

# ------------------------------------------------------------
# chat export (markdown / json download)
# ------------------------------------------------------------

def chat_export_md(bot, chat):
    who_user = "You"
    who_bot = bot["name"] or "Bot"
    lines = ["# %s" % (chat.get("title") or "chat"), ""]
    meta = "*bot: %s" % who_bot
    if chat.get("model"):
        meta += " · model: %s" % chat["model"]
    meta += " · exported: %s*" % time.strftime("%Y-%m-%d %H:%M")
    lines += [meta, "", "---", ""]
    for m in chat.get("messages", []):
        who = who_user if m.get("role") == "user" else who_bot
        body = (m.get("content") or "").strip()
        if m.get("images"):
            body = "_[%d picture%s attached]_ %s" % (
                len(m["images"]), "s" if len(m["images"]) != 1 else "", body)
        lines += ["**%s:**" % who, "", body or "_(empty)_", ""]
    return "\n".join(lines)

# ------------------------------------------------------------
# HTTP handler
# ------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "kitsune-ai-mangr/" + VERSION
    protocol_version = "HTTP/1.1"   # required for chunked streaming

    def log_message(self, fmt, *args):
        sys.stdout.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ---- helpers ----
    def send_json(self, obj, code=200):
        body = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode())
        except Exception:
            return {}

    def chunks(self, obj):
        data = json.dumps(obj, separators=(",", ":")).encode() + b"\n"
        self.wfile.write(("%x\r\n" % len(data)).encode() + data + b"\r\n")
        self.wfile.flush()

    def stream_start(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    # ---- routing ----
    def do_GET(self):
        path = self.path.split("?")[0].strip("/")
        try:
            if path == "" or path == "index.html":
                return self.serve_index()
            if path == "favicon.ico":
                return self.serve_file(os.path.join(BASE, "icon-192.png"), "image/png")
            if path in ("icon-192.png", "icon-512.png"):
                return self.serve_file(os.path.join(BASE, path), "image/png")
            if path == "avatar.png":
                return self.serve_file(DEFAULT_AVATAR, "image/png")
            if path == "logo.jpg":
                return self.serve_file(os.path.join(BASE, "logo.jpg"), "image/jpeg")
            if path == "robot.png":
                return self.serve_file(os.path.join(BASE, "robot.png"), "image/png")
            if path == "manifest.webmanifest":
                return self.serve_manifest()
            if path == "sw.js":
                return self.serve_file(os.path.join(BASE, "sw.js"),
                                       "text/javascript; charset=utf-8", fallback=SW_SOURCE)
            if path == "api/health":
                return self.send_json({"ok": True, "app": "kitsune//ai-mangr", "version": VERSION,
                                       "ollama": ollama_ok(max_age=0),
                                       "models": len(ollama_models())})
            if path == "api/lan":
                return self.send_json(lan_info())
            if path == "api/models":
                return self.send_json({"models": ollama_models(), "default_model": DEFAULT_MODEL})
            if path == "api/vision":
                # does the picked model see pictures? the ui hides the
                # attach button unless this says true
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                model = (q.get("model") or [""])[0].strip() or DEFAULT_MODEL
                return self.send_json({"model": model, "vision": model_can_see(model)})
            if path == "api/settings":
                return self.send_json({"single_model": single_model_enabled()})
            if path == "api/bots":
                return self.send_json({"bots": list_bots()})
            m = re.match(r"^api/bots/([\w-]+)/chats$", path)
            if m:
                return self.send_json({"chats": list_chats(m.group(1))})
            m = re.match(r"^api/bots/([\w-]+)/export$", path)
            if m:
                return self.handle_export(m.group(1))
            m = re.match(r"^api/bots/([\w-]+)/avatar$", path)
            if m:
                return self.handle_avatar(m.group(1))
            m = re.match(r"^api/bots/([\w-]+)$", path)
            if m:
                b = load_bot(m.group(1))
                if not b:
                    return self.send_json({"error": "no such bot"}, 404)
                return self.send_json({"bot": b})
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)$", path)
            if m:
                try:
                    return self.send_json({"chat": load_chat(m.group(1), m.group(2))})
                except Exception:
                    return self.send_json({"error": "no such chat"}, 404)
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)/export$", path)
            if m:
                fmt = (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                       .get("fmt") or ["md"])[0]
                return self.handle_chat_export(m.group(1), m.group(2), fmt)
            self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try: self.send_json({"error": str(e)}, 500)
            except Exception: pass

    def do_POST(self):
        path = self.path.split("?")[0].strip("/")
        try:
            if path == "api/bots":
                b = self.read_body()
                if not b.get("name"):
                    return self.send_json({"error": "name required"}, 400)
                name = slug(b["name"])
                if find_bot_file(name):
                    return self.send_json({"error": "a bot file named %s.ai already exists" % name}, 409)
                icon = save_data_image(b.get("icon"), name)   # picked picture -> avatars/
                if icon:
                    b["avatar"] = icon
                write_ai(name, b)
                return self.send_json({"ok": True, "name": name})
            if path == "api/import":
                return self.handle_import()
            m = re.match(r"^api/bots/([\w-]+)/edit$", path)
            if m:
                return self.handle_bot_edit(m.group(1))
            m = re.match(r"^api/bots/([\w-]+)/copy$", path)
            if m:
                return self.handle_bot_copy(m.group(1))
            if path == "api/settings":
                b = self.read_body()
                if "single_model" in b:
                    set_single_model(bool(b.get("single_model")))
                return self.send_json({"ok": True, "single_model": single_model_enabled()})
            if path == "api/chat":
                return self.handle_chat()
            if path == "api/regen":
                return self.handle_regen()
            if path == "api/continue":
                return self.handle_continue()
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)/edit$", path)
            if m:
                return self.handle_edit(m.group(1), m.group(2))
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)/delete$", path)
            if m:
                return self.handle_delete_msg(m.group(1), m.group(2))
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)/rename$", path)
            if m:
                return self.handle_rename(m.group(1), m.group(2))
            self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try: self.send_json({"error": str(e)}, 500)
            except Exception: pass

    def do_DELETE(self):
        path = self.path.split("?")[0].strip("/")
        try:
            m = re.match(r"^api/bots/([\w-]+)$", path)
            if m:
                p = find_bot_file(m.group(1))
                if p:
                    os.remove(p)
                    # the bot's chats and its generated icon are theirs alone - gone too
                    shutil.rmtree(os.path.join(CHATS_DIR, m.group(1)), ignore_errors=True)
                    if os.path.isdir(AVATARS_DIR):
                        for fn in os.listdir(AVATARS_DIR):
                            if re.match(r"^%s-icon\." % re.escape(m.group(1)), fn):
                                try: os.remove(os.path.join(AVATARS_DIR, fn))
                                except Exception: pass
                    return self.send_json({"ok": True})
                return self.send_json({"error": "no such bot"}, 404)
            m = re.match(r"^api/chats/([\w-]+)/([0-9]+)$", path)
            if m:
                try:
                    os.remove(chat_file(m.group(1), m.group(2)))
                    return self.send_json({"ok": True})
                except Exception:
                    return self.send_json({"error": "no such chat"}, 404)
            self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try: self.send_json({"error": str(e)}, 500)
            except Exception: pass

    # ---- the main event: chat with streaming ----
    def handle_chat(self):
        body = self.read_body()
        bot = load_bot(body.get("bot", ""))
        if not bot:
            return self.send_json({"error": "no such bot"}, 404)
        model = body.get("model") or bot.get("model") or DEFAULT_MODEL
        user_msg = (body.get("message") or "").strip()
        try:
            images = clean_images(body.get("images"))
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)
        if not user_msg and not images:
            return self.send_json({"error": "empty message"}, 400)

        # find or create the chat file
        chat_id = str(body.get("chat_id") or "")
        chat = None
        if chat_id and re.match(r"^[0-9]+$", chat_id):
            try:
                chat = load_chat(bot["file"][:-3], chat_id)
            except Exception:
                chat = None
        if chat is None:
            chat_id = str(int(time.time() * 1000))
            chat = {"id": chat_id, "title": user_msg[:60] or "(picture)",
                    "model": model, "messages": []}
            # the greeting is the bot's opening turn, stored once
            if bot.get("greeting"):
                chat["messages"].append({"role": "assistant", "content": bot["greeting"]})

        chat["model"] = model
        entry = {"role": "user", "content": user_msg}
        if images:
            entry["images"] = images
        chat["messages"].append(entry)
        save_chat(bot["file"][:-3], chat)
        self._stream_reply(bot, chat, model)

    # ---- build the ollama message list for a turn ----
    def _prep_messages(self, bot, chat, model, hidden_user=None):
        messages = [{"role": "system", "content": system_prompt(bot)}] + chat["messages"]
        if hidden_user:
            # continue: a nudge the model sees but the chat file never stores
            messages.append({"role": "user", "content": hidden_user})
        if model_can_see(model) is False:
            # known-blind model: drop the pictures so ollama won't choke.
            # they stay saved in the chat file for when a vision model is back.
            messages = [{k: v for k, v in m.items() if k != "images"} for m in messages]
        return messages

    # ---- shared streaming tail: meta + tokens, reply persisted after ----
    def _stream_reply(self, bot, chat, model, hidden_user=None):
        # pre-flight: fail fast with a message a human can act on
        if not ollama_ok():
            return self._ollama_down()
        enforce_single_model(model)   # one-model mode: drop the others from ram
        messages = self._prep_messages(bot, chat, model, hidden_user)
        self.stream_start()
        reply = ""
        try:
            self.chunks({"t": "meta", "chat_id": chat["id"], "model": model, "bot": bot["name"]})
            for tok in ollama_chat_stream(model, messages, bot_options(bot)):
                reply += tok
                self.chunks({"t": "tok", "v": tok})
        except (BrokenPipeError, ConnectionResetError):
            # phone walked away - keep whatever the model said so far
            pass
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode()[:300]
            except Exception:
                detail = ""
            try:
                self.chunks({"t": "err", "e": self._friendly_ollama_error(e.code, detail, e.reason)})
            except Exception:
                pass
        except Exception as e:
            try:
                self.chunks({"t": "err", "e": str(e)})
            except Exception:
                pass
        # persist the reply (full or partial)
        if reply:
            chat["messages"].append({"role": "assistant", "content": reply})
            save_chat(bot["file"][:-3], chat)
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except Exception:
            pass

    @staticmethod
    def _friendly_ollama_error(code, detail, reason):
        """turn ollama's raw error json into something a human can act on"""
        msg = ""
        try:
            msg = str(json.loads(detail).get("error") or "")
        except Exception:
            msg = detail or (reason or "")
        m = re.search(r"model\s+[\"']?([\w.:/-]+)[\"']?\s+not found", msg, re.I)
        if m or "pull it first" in msg or "not found, try pulling" in msg:
            name = m.group(1) if m else ""
            return "model %s is not installed - run: ollama pull %s" % (
                "'%s'" % name if name else "(unknown)", name or "<model>")
        if code == 404:
            return "model not found in ollama - check the name, or run: ollama pull <model>"
        return "Ollama %s: %s" % (code, msg or reason or "error")

    def _ollama_down(self):
        """sent instead of a stream when ollama isn't running at all"""
        try:
            self.send_json({"error": "ollama is not reachable - start it with: ollama serve"}, 503)
        except Exception:
            pass

    # ---- regenerate: drop the last reply, stream a fresh one ----
    def handle_regen(self):
        body = self.read_body()
        bot = load_bot(body.get("bot", ""))
        if not bot:
            return self.send_json({"error": "no such bot"}, 404)
        chat_id = str(body.get("chat_id") or "")
        if not re.match(r"^[0-9]+$", chat_id):
            return self.send_json({"error": "no chat id"}, 400)
        try:
            chat = load_chat(bot["file"][:-3], chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        model = body.get("model") or chat.get("model") or bot.get("model") or DEFAULT_MODEL
        while chat["messages"] and chat["messages"][-1]["role"] == "assistant":
            chat["messages"].pop()
        if not chat["messages"] or chat["messages"][-1]["role"] != "user":
            return self.send_json({"error": "nothing to regenerate"}, 400)
        save_chat(bot["file"][:-3], chat)
        self._stream_reply(bot, chat, model)

    # ---- continue: keep the last reply going ----
    def handle_continue(self):
        body = self.read_body()
        bot = load_bot(body.get("bot", ""))
        if not bot:
            return self.send_json({"error": "no such bot"}, 404)
        chat_id = str(body.get("chat_id") or "")
        if not re.match(r"^[0-9]+$", chat_id):
            return self.send_json({"error": "no chat id"}, 400)
        try:
            chat = load_chat(bot["file"][:-3], chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        model = body.get("model") or chat.get("model") or bot.get("model") or DEFAULT_MODEL
        hidden = CONTINUE_NUDGE if (chat["messages"] and
                                    chat["messages"][-1]["role"] == "assistant") else None
        self._stream_reply(bot, chat, model, hidden_user=hidden)

    # ---- edit your last message - replies after it are dropped ----
    def handle_edit(self, bot_slug, chat_id):
        body = self.read_body()
        content = (body.get("content") or "").strip()
        if not content:
            return self.send_json({"error": "empty message"}, 400)
        try:
            chat = load_chat(bot_slug, chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        idx = next((i for i in range(len(chat["messages"]) - 1, -1, -1)
                    if chat["messages"][i]["role"] == "user"), None)
        if idx is None:
            return self.send_json({"error": "no user message to edit"}, 400)
        chat["messages"][idx]["content"] = content
        del chat["messages"][idx + 1:]
        save_chat(bot_slug, chat)
        return self.send_json({"ok": True, "messages": len(chat["messages"])})

    # ---- delete your last message (+ the reply that followed it) ----
    def handle_delete_msg(self, bot_slug, chat_id):
        try:
            chat = load_chat(bot_slug, chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        idx = next((i for i in range(len(chat["messages"]) - 1, -1, -1)
                    if chat["messages"][i]["role"] == "user"), None)
        if idx is None:
            return self.send_json({"error": "no user message to delete"}, 400)
        end = idx + 1
        if end < len(chat["messages"]) and chat["messages"][end]["role"] == "assistant":
            end += 1
        del chat["messages"][idx:end]
        save_chat(bot_slug, chat)
        return self.send_json({"ok": True, "messages": len(chat["messages"])})

    # ---- rename a chat (the chats menu's pencil): title lives in the json ----
    def handle_rename(self, bot_slug, chat_id):
        body = self.read_body()
        title = str(body.get("title", "")).strip()[:80]
        if not title:
            return self.send_json({"error": "title required"}, 400)
        try:
            chat = load_chat(bot_slug, chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        chat["title"] = title
        save_chat(bot_slug, chat)
        return self.send_json({"ok": True, "title": title})

    # ---- export a chat as markdown (or json) download ----
    def handle_chat_export(self, bot_slug, chat_id, fmt):
        try:
            chat = load_chat(bot_slug, chat_id)
        except Exception:
            return self.send_json({"error": "no such chat"}, 404)
        bot = load_bot(bot_slug) or {"name": bot_slug}
        if fmt == "json":
            body = json.dumps(chat, ensure_ascii=False, indent=1).encode()
            name = "%s-chat-%s.json" % (slug(bot_slug), chat_id)
            ctype = "application/json"
        else:
            body = chat_export_md(bot, chat).encode()
            name = "%s-chat-%s.md" % (slug(bot_slug), chat_id)
            ctype = "text/markdown; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    # ---- edit an existing bot from the manager menu: same fields as create,
    # but the .ai file (and its chats) keep their name/slug ----
    def handle_bot_edit(self, slugid):
        body = self.read_body()
        p = find_bot_file(slugid)
        if not p:
            return self.send_json({"error": "no such bot"}, 404)
        b = parse_ai(p)
        for k in ("name", "description", "greeting", "color", "model",
                  "temperature", "max_tokens"):
            if k in body:
                b[k] = str(body.get(k) or "").strip()
        if not b["name"]:
            b["name"] = slugid.replace("-", " ").title()
        icon = save_data_image(body.get("icon"), slugid)   # a freshly picked picture
        if icon:
            b["avatar"] = icon
        write_ai_to(p, b, slugid)   # same file, same slug, chats stay put
        return self.send_json({"ok": True, "bot": parse_ai(p)})

    # ---- duplicate a bot: fresh .ai file (+ its generated icon), new name ----
    def handle_bot_copy(self, slugid):
        body = self.read_body()
        src = find_bot_file(slugid)
        if not src:
            return self.send_json({"error": "no such bot"}, 404)
        b = parse_ai(src)
        new_name = str(body.get("name") or "").strip() or (b["name"] + " copy")
        newid = slug(new_name)
        if find_bot_file(newid):
            return self.send_json({"error": "a bot file named %s.ai already exists" % newid}, 409)
        av = (b.get("avatar") or "").strip()
        m = re.match(r"^avatars/([\w][\w .()-]*\.(?:png|jpe?g|gif|webp))$", av, re.I)
        if m and re.match(r"^%s-icon\." % re.escape(slugid), m.group(1), re.I):
            oldfile = os.path.join(AVATARS_DIR, m.group(1))
            if os.path.isfile(oldfile):
                ext = os.path.splitext(m.group(1))[1].lower()
                newfile = "%s-icon%s" % (newid, ext)
                os.makedirs(AVATARS_DIR, exist_ok=True)
                shutil.copyfile(oldfile, os.path.join(AVATARS_DIR, newfile))
                b["avatar"] = "avatars/" + newfile
        b["name"] = new_name
        write_ai_to(bot_path(newid), b, newid)
        return self.send_json({"ok": True, "name": newid})

    # ---- import .ai files: upload from the device, or straight from a url ----
    MAX_IMPORT = 512 * 1024

    def handle_import(self):
        body = self.read_body()
        overwrite = bool(body.get("overwrite"))
        if body.get("url"):
            u = str(body["url"]).strip()
            if not re.match(r"^https?://", u):
                return self.send_json({"error": "only http(s) urls"}, 400)
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "kitsune-ai-mangr"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    data = r.read(self.MAX_IMPORT + 1)
            except Exception as e:
                return self.send_json({"error": "could not fetch url: %s" % e}, 502)
            fname = os.path.basename(u.split("?")[0]) or ""
        else:
            fname = os.path.basename(str(body.get("filename") or ""))
            data = str(body.get("content") or "").encode("utf-8", "replace")
        if not fname.lower().endswith(".ai"):
            fname = (fname or "imported") + ".ai"
        if not data or len(data) > self.MAX_IMPORT:
            return self.send_json({"error": "empty or too large (512kb cap)"}, 400)
        try:
            text = data.decode("utf-8-sig")
        except Exception:
            return self.send_json({"error": "not utf-8 text - is that really a .ai file?"}, 400)
        # validate it parses BEFORE it lands in bots/
        os.makedirs(BOTS_DIR, exist_ok=True)
        tmppath = os.path.join(BOTS_DIR, ".import-check.tmp")
        try:
            with open(tmppath, "w", encoding="utf-8") as f:
                f.write(text)
            b = parse_ai(tmppath)
        except Exception as e:
            return self.send_json({"error": "not a valid .ai file: %s" % e}, 400)
        finally:
            if os.path.exists(tmppath):
                os.remove(tmppath)
        name = slug(os.path.splitext(fname)[0])
        if find_bot_file(name) and not overwrite:
            return self.send_json({"error": "a bot file named %s.ai already exists - overwrite it?" % name,
                                   "exists": True, "slug": name}, 409)
        with open(bot_path(name), "w", encoding="utf-8") as f:
            f.write(text if text.endswith("\n") else text + "\n")
        return self.send_json({"ok": True, "name": name, "bot": b["name"]})

    # ---- export: download a bot's .ai file (share it, back it up, feed a market) ----
    def handle_export(self, bot_slug):
        p = find_bot_file(bot_slug)
        if not p:
            return self.send_json({"error": "no such bot"}, 404)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            return self.send_json({"error": "unreadable file"}, 500)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Disposition",
                         'attachment; filename="%s.ai"' % slug(bot_slug))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    # ---- profile picture: the bot's avatar file, else the default avatar.png ----
    def handle_avatar(self, bot_slug):
        p = None
        bot = load_bot(bot_slug)
        if bot and bot.get("avatar"):
            p = resolve_avatar(bot["avatar"])
        if not p:
            p = DEFAULT_AVATAR
        if os.path.isfile(p):
            return self.serve_file(p, avatar_mime(p))
        self.send_response(204); self.end_headers()

    def serve_file(self, path, ctype, fallback=None):
        data = None
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception:
            data = fallback.encode() if fallback else None
        if data is None:
            self.send_response(204); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def serve_manifest(self):
        bg = theme_map().get("background", "#0f1216")
        man = {"name": "kitsune//ai-mangr", "short_name": "ai-mangr", "id": "/",
               "start_url": "/", "scope": "/", "display": "standalone",
               "background_color": bg, "theme_color": bg,
               "description": "your own local AI chat manager, powered by ollama",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192",
                          "type": "image/png", "purpose": "any maskable"},
                         {"src": "/icon-512.png", "sizes": "512x512",
                          "type": "image/png", "purpose": "any maskable"}]}
        self.send_json(man)

    def serve_index(self):
        body = None
        for p in INDEX_CANDIDATES:
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as f:
                        body = f.read()
                    break
                except Exception:
                    pass
        if body is None:
            # self-diagnosing page: show exactly what is wrong and where
            try:
                listing = ", ".join(sorted(os.listdir(BASE))) or "(empty folder)"
            except Exception:
                listing = "(unreadable)"
            looked = "<br>it looked in: " + "<br>&nbsp;&nbsp;".join(INDEX_CANDIDATES)
            body = (("<h1>kitsune//ai-mangr</h1>"
                     "<p><b>index.html is missing</b> - put it next to server.py "
                     "(copy it out of the zip you downloaded, never delete it).</p>"
                     "<p>server.py lives in: <code>%s</code>%s</p>"
                     "<p>that folder currently contains: %s</p>")
                    % (BASE, looked, listing)).encode()
        inject = load_theme()
        bg = theme_map().get("background")
        if bg:
            inject += '<meta name="theme-color" content="%s">' % bg
        if inject:
            body = body.replace(b"</head>", inject.encode() + b"</head>", 1)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

# ------------------------------------------------------------

def bind_server():
    """one address, always: try THE port, and if it's genuinely taken by
    something else, refuse to start with a clear message - no silent port
    hopping (that silently changed the address and broke phone bookmarks)."""
    try:
        return ThreadingHTTPServer((HOST, PORT), Handler), PORT, None
    except OSError as e:
        return None, PORT, e

def main():
    migrate_configs()   # tuck root theme.conf/settings.conf into config/ (old installs)
    os.makedirs(BOTS_DIR, exist_ok=True)
    os.makedirs(CHATS_DIR, exist_ok=True)
    srv, port, err = bind_server()
    if srv is None:
        print("", flush=True)
        print("  port %d is already taken - kitsune//ai-mangr will not steal another port." % PORT, flush=True)
        print("  one address, always: fixing the port IS the feature.", flush=True)
        print("", flush=True)
        print("  what to do:", flush=True)
        print("    - bash start.sh          -> it stops a stale copy of this app and retries", flush=True)
        print("    - or free port %d yourself (the squatter: %s)" % (PORT, err), flush=True)
        print("    - or last resort: PORT=%d bash start.sh  (address changes!)" % (PORT + 1), flush=True)
        print("", flush=True)
        sys.exit(1)
    try:
        with open(PORT_FILE, "w") as f:
            f.write(str(port))
    except OSError:
        pass
    def drop_portfile(*a):
        try:
            os.unlink(PORT_FILE)
        except OSError:
            pass
    def _bye(*a):
        drop_portfile()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, _bye)
    print("kitsune//ai-mangr v%s" % VERSION, flush=True)
    print("  on this pc : http://localhost:%d" % port, flush=True)
    if HOST != "127.0.0.1":
        ips = lan_ips()
        for ip in ips:
            print("  from phone : http://%s:%d   <- same wifi, one address, always" % (ip, port), flush=True)
        if not ips:
            print("  from phone : (no LAN ip found - is wifi/network connected?)", flush=True)
        host = socket.gethostname().split(".")[0]
        if host:
            print("  also tries : http://%s.local:%d   (survives ip changes)" % (host, port), flush=True)
        print("  phone setup: open the url there -> share menu -> add to home screen", flush=True)
    else:
        print("  bind       : 127.0.0.1 only (BIND=0.0.0.0 to let your phone in)", flush=True)
    print("  ollama     : %s" % OLLAMA, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("bye", flush=True)
    finally:
        drop_portfile()
        try:
            srv.server_close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
