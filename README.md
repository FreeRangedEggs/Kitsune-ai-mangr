# kitsune//ai-mangr — extensions

A home for add-ons that plug into [kitsune//ai-mangr](kitsune-ai-mangr/README.md) — a private, local AI chat manager for Ollama — without touching its code.

```
   )\      kitsune//ai-mangr  = your web AI manager (chat, bots, ollama)
  (  )     extensions/       = this repo: what the manager was missing
 ( (  )    one manifest     = extension.json, and the manager finds it
 _)..--.._
```

| Folder | What it is |
| --- | --- |
| [`kitsune-ai-mangr/`](kitsune-ai-mangr/) | the manager itself, clean v2.0.4 — with the built-in **extension manager** (settings > app) |
| [`vimoon-extension/`](vimoon-extension/README.md) | **ViMoon** — a moonlit code editor with vim keys that lives inside the manager |

The two are fully separate: kitsune runs fine with zero extensions, and ViMoon is a self-contained folder with its own installer, uninstaller and README. Nothing in kitsune's tree is modified except three CSP directives (reversible, backed up, done by ViMoon's installer).

---

## Install order

```bash
# 1. the manager (if you do not have it yet)
git clone https://github.com/you/this-repo extensions && cd extensions
bash kitsune-ai-mangr/install.sh && kitsune

# 2. any extension - they install into the kitsune folder
cd vimoon-extension
bash install.sh                 # auto-finds kitsune, or: --dir /path/to/kitsune-ai-mangr
bash /path/to/kitsune-ai-mangr/vimoon.sh

# 3. restart kitsune once (the CSP widening), refresh the browser
```

Open **http://localhost:8788**, click the gear, expand **app** — the new **extensions** block lists every installed add-on with a live status chip and **start / stop / launch** buttons. ViMoon shows up on its own, no registration step beyond running its installer.

---

## The manifest: `extension.json`

An extension is any folder next to `server.py` (or inside `extensions/`) that ships an `extension.json`. The manager scans one level deep on every request and lists what it finds:

```json
{
  "id": "vimoon",
  "name": "ViMoon",
  "version": "1.0.0",
  "description": "moonlit code editor - vim keys, 20+ languages, completion, MoonBot (ollama), git panel, multi-tab.",
  "author": "you",
  "entry": {
    "port": 8790,
    "health": "/api/health",
    "health_app": "vimoon-extension",
    "url": "http://localhost:8790"
  },
  "control": "vimoon.sh",
  "docs": "vimoon/README.md"
}
```

| Field | Required | What the manager does with it |
| --- | --- | --- |
| `id` | yes | unique key (`[\w-]+`); also matches the launch button to an injected top-bar button |
| `name`, `version`, `description` | suggested | shown on the row; the live version replaces the manifest one once the health probe answers |
| `entry.url` + `entry.health` | optional | the manager probes `url + health` with a 0.5 s budget - that is the **running :port** chip. `entry.health_app` (optional) makes the probe verify the responder really is this extension |
| `entry.port` | optional | shown in the chip |
| `control` | optional | path to a `start / stop / restart / status` shell script **relative to the kitsune folder**. powers the start/stop buttons |

### What the manager guarantees

- start/stop is always exactly `bash <control> <action>` — one argument vector, no shell string, so there is nothing to inject.
- the control script is resolved with `realpath` and must sit **inside the kitsune folder**; anything else silently drops the buttons.
- all manifest fields are length-capped and type-checked server side.
- the list is cached for 2 s, and every mutation busts the cache, so the chip never lies.
- the API is `GET /api/extensions` and `POST /api/extensions/action {id, action}` — same-origin only, behind the PIN lock like everything else.

### Building your own

1. make a folder with your code and an `extension.json` (copy the one above to start).
2. if it runs a server: give it a fixed port, a `/api/health`-style endpoint answering `{"ok": true, "app": "<your id>"}`, and put `entry` in the manifest.
3. if it should be start/stop-able from the manager: ship a control script (`case "$1" in start|stop|restart|status) ...`) and point `control` at it.
4. drop the folder next to kitsune's `server.py`, open settings > app, hit refresh.

That is the whole contract. No build step, no SDK, no registration — a folder with a JSON file is an extension.

---

## Extension gallery

| Extension | What you get |
| --- | --- |
| **[ViMoon](vimoon-extension/README.md)** `v1.0.0` | a full code editor inside the manager: dreamy moonlight theme (plus dark + dawn), complete vim keymap, 20+ language syntax highlighting, context-aware completion + ollama ghost text, MoonBot chat with streaming, multi-file tabs, in-file & project-wide search/replace, git panel (stage / commit / history / diffs), plugin system. Its workspace **is** the kitsune folder — edits to bots, knowledge and configs save straight to disk where the manager reads them. |

---

## Files

```
extensions/
├── README.md               you are here - manifest spec + gallery
├── kitsune-ai-mangr/       the manager (see its README.md)
└── vimoon-extension/       the ViMoon extension (see its README.md)
```

Both projects are plain-python / plain-HTML with zero pip dependencies and ship their own uninstallers. Demo videos and screenshots live inside `vimoon-extension/demo/` and `vimoon-extension/screenshots/`.
