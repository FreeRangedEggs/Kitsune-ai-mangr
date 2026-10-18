# kitsune//ai-mangr

A private, local chat app for [Ollama](https://ollama.com) models. Make bots with their own personalities, talk to them from your PC or your phone, give them files to read, and keep every word on your own machine.

- **Zero dependencies.** The whole server is one plain `python3` file.
- **Fully local.** Chats, bots and files live in this folder. Nothing is sent anywhere.
- **One fixed address.** The app always answers on port `8788`, so a phone bookmark or home-screen icon never breaks.
- **Phone friendly.** Installable as a home-screen app, with a UI built for small screens.

---

## Quick start

You need **Python 3** and **Ollama** with at least one model pulled (for example `ollama pull dolphin3:8b`).

```bash
bash install.sh      # one-time: puts the `kitsune` command in your PATH
kitsune              # start the app
```

Open **http://localhost:8788**, pick a persona, and talk.

Prefer not to install anything? From this folder, `bash start.sh` does the same thing.

---

## The `kitsune` command

`install.sh` adds a small launcher called `kitsune` to `~/.local/bin` and makes sure that folder is in your PATH. Open a new terminal afterwards (or run `source ~/.bashrc`).

| Command | What it does |
| --- | --- |
| `kitsune` | Starts the app. If it is already running, it restarts it. |
| `kitsune stop` | Stops the app. |
| `kitsune status` | Shows whether the app is running and whether Ollama is reachable. |
| `kitsune warm` | Starts the app and loads the model into RAM now, instead of on your first message. |
| `kitsune warm <model>` | Same, but warms a specific model. |
| `kitsune tunnel` | Opens a temporary https link with a QR code, for use away from home. |

Notes:

- Nothing is copied. The launcher points at this folder, so if you move the folder, run `bash install.sh` again.
- `bash install.sh --dir /some/folder` installs the launcher somewhere else.
- `bash install.sh --uninstall` removes the launcher and the PATH line it added.
- Environment variables: `PORT=...` changes the port, `BIND=127.0.0.1 kitsune` keeps the app reachable from this PC only (the phone and tunnel stop working).

---

## Using it on your phone

Your phone and PC must be on the same wifi.

1. Start the app on the PC. It prints your **one address**, like `http://192.168.1.23:8788`.
2. On the PC, the phone button in the top bar also shows the address and a **QR code**. Scan it with your phone camera.
3. Add it to your home screen:
   - **Android:** Chrome, open the address, menu, "Add to home screen".
   - **iPhone:** Safari, open the address, share, "Add to home screen".

It then opens like an app, full screen.

For an address that never changes, either reserve your PC's IP in your router (a DHCP static lease), or use the hostname form the phone menu offers, `http://<your-pc-name>.local:8788`.

Away from home, `kitsune tunnel` gives a temporary https link. It needs [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) installed, and the link dies when the tunnel stops.

---

## Personas

The bots menu (the robot button) lists every persona. Tap one to open it. The pencil edits it, the double arrow duplicates it, and the x deletes it along with its chats.

Included personas:

| Persona | What it is |
| --- | --- |
| **Aria** | Tavern keeper roleplay. |
| **Kit** | A playful fox spirit. |
| **Coder** | Senior-engineer helper, set to `qwen2.5-coder:7b`. |
| **Tutor** | Patient teacher for any subject. |
| **Dungeon Master** | Text-adventure game master. |
| **Editor** | Writing editor. Fixes clarity and keeps your voice. |
| **Producer** | Music production mentor. |
| **Detective Voss** | Hard-boiled noir private eye. |
| **Bot** | Plain default bot. |

Only Coder sets a model. The others use whatever model is picked in the chat menu.

### Making your own

Use **+ new bot** in the bots menu, or drop a plain-text `.ai` file into `bots/` and refresh the page:

```
name: "Aria"
description: "who she is, how she talks - becomes the system prompt"
greeting: "*looks up* Rough night to be out. Sit by the fire."
color: "#d4a373"
model: "dolphin3:8b"
temperature: "0.9"
max_tokens: "400"
icon: "avatars/aria-icon.png"
```

Only `name`, `description` and `greeting` matter. Everything else is optional. A line that is not `key: value` continues the field above it, so multi-line descriptions work. See `bots/README.txt` for every field.

### Sharing bots

- **export** downloads the current bot's `.ai` file.
- **import** loads `.ai` files from your device (pick several at once).
- **url** installs a `.ai` file straight from a link, such as a raw GitHub file.

---

## Chat features

- Code blocks and inline code render in chat.
- Under your last message: **edit** and **delete**. Under the bot's last reply: **copy**, **redo** and **continue**.
- The send button turns into **stop** while a reply streams.
- **Export a chat** as markdown from the chats menu.
- Paste or drag screenshots into the chat.
- Friendly errors, such as "ollama is not reachable - start it with: ollama serve" or "model 'x' is not installed - run: ollama pull x".

### The + button

The **+** next to the message box opens your device's file picker and imports what you choose:

- **Pictures** attach to your next message (vision models only).
- **`.ai` files** become new bots.
- **Text, code and data files** go into the open bot's knowledge. Dragging files onto the chat does the same.

### Pictures (vision models)

The paperclip attaches up to 4 photos per message, shrunk to 1280px. It only shows for models that can see (`llava`, `minicpm-v`, `moondream`, `gemma` and similar, as reported by Ollama). Text-only models never receive the pictures, but the chat keeps them for when you switch back to a vision model.

---

## Knowledge files

Attach text files to a bot and it reads them when it answers (bot menu, edit, "+ add files", or the **+** button).

- Allowed: `txt`, `md`, `py`, `json`, `csv`, `html` and other plain-text types. Not PDF. Run `pdftotext file.pdf` first.
- Limits: 2 MB per file, 50 files per bot.
- A small pile (under about 6000 characters) goes into the prompt in full. A bigger pile is cut into chunks, and the best matches for your last two messages are picked using keyword scoring, with no extra software.
- Chunks per reply is adjustable (default 4, max 12).
- Files live in `knowledge/<bot>/`. Duplicating a bot copies its files, and deleting a bot deletes them.
- The context window is raised to 4096 automatically when knowledge is used. More context means more RAM.

---

## Model maker

Inside the bot form, the **model maker** section lets you tune a bot. Every box is optional.

| Field | Purpose |
| --- | --- |
| style | `character` (roleplay) or `assistant` (tutor or coder, no forced in-character rules) |
| system | Your own system prompt, replacing the auto-built one |
| examples | Sample dialogue so the model copies the voice |
| top_p, top_k, repeat_penalty, seed | Sampling controls |
| num_ctx | Context window size |
| stop | Stop words, separated by `\|` |

**Download as an Ollama Modelfile** bakes a bot into a real model:

```bash
ollama create mybot -f mybot.Modelfile
```

---

## Settings and themes

The gear button has three sections:

- **This device:** text size, message width, compact spacing, enter-key behaviour. Stored in this browser only, so phone and PC can differ.
- **Theme:** presets (fox, amoled, light, catppuccin, gruvbox, dracula), a color picker for every color, font, base text size and bubble roundness. It previews live. Cancel undoes it, and save writes `config/theme.conf` so every device gets the same look.
- **App:** one-model-at-a-time mode, the PIN lock, and the terminal switch (all in `config/settings.conf`).

**One model at a time** (`single_model on`) unloads every other model from RAM before each reply, so two models never share your memory. Useful on 8 GB machines.

You can also edit `config/theme.conf` by hand. Save and refresh the browser. Presets are included as commented blocks at the bottom of the file.

---

## PIN lock (optional)

Set a PIN in settings, App, and every page and API call needs an unlock on every device.

- Only a salted hash is stored. The PIN itself is never written down.
- Unlocking gives the device a session cookie for 7 days. Restarting the server signs everyone out.
- 5 wrong tries from one IP means a 30 second wait.

**Locked out?** Stop the server, delete the `pin_hash`, `pin_salt` and `pin_iters` lines from `config/settings.conf`, and start again.

The app speaks plain http on your wifi, so this is casual protection. It keeps flatmates and guests out of the UI, but it does not encrypt traffic. For more, use `BIND=127.0.0.1` (this PC only) or the tunnel for https.

---

## Web terminal (optional, off by default)

A small console and file browser that runs on the machine hosting the server, like ssh from the browser. Open it from the bots menu (`>_ terminal`) or settings, App. The switch at the top of the panel turns it on.

- **Console:** one command at a time, output capped, killed after 120 seconds. Your working folder is remembered, so `cd`, `cd ~`, `cd ..` and `cd -` work, and the prompt shows where you are. Quick buttons run Windows commands on a Windows host and Linux commands elsewhere. Interactive programs (vim, a Python REPL) do not work.
- **File browser and editor:** reaches your home folder plus this project. Edits keep a `.term-bak` copy of the old file. `server.py` and `index.html` are write-locked here on purpose. Each file row has an **import** button that copies it into the open bot's knowledge.

> **Security: read this.** While the terminal is on, anyone who can open the app can run anything on that machine. Keep it off when you do not need it, set a PIN (every terminal call then needs the PIN too), and **never expose the app to the public internet with the terminal on.**

---

## Music player

The note button plays a shuffle of the songs in your `~/Music` folder (subfolders count as albums). Play, skip and volume are all there is. Closing the panel keeps the music going, and the button glows while something plays.

Formats are whatever your browser can decode (mp3, m4a, ogg, opus, flac, wav, webm). Up to 2000 songs per scan. It is read-only and locked inside the Music folder.

---

## Files in this folder

```
server.py        the whole server (plain python3, no dependencies)
index.html       the UI, sits right next to server.py
start.sh         start / stop / status / warm
install.sh       puts the `kitsune` command in your PATH
tunnel.sh        temporary https link + QR for away from home
sw.js            service worker (needed for "add to home screen")
bots/            one .ai file per persona
chats/           chat history, one json file per chat
knowledge/       files attached to bots (created on first use)
avatars/         bot icons picked in the UI
config/
  theme.conf         theme, kitty-style: edit a line, save, refresh
  settings.conf      app switches, written by the gear button
  settings.conf.example  template for the above
avatar.png       default bot picture (swap it freely)
logo.jpg, robot.png, icon-192.png, icon-512.png   branding and app icons
```

`chats/`, `knowledge/`, `avatars/` and `config/settings.conf` are in `.gitignore`, so your conversations, files and PIN hash stay out of git.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `kitsune: command not found` | Open a new terminal, or run `source ~/.bashrc`. If it still fails, run `bash install.sh` again. |
| "ollama is not reachable" | Start it with `ollama serve`. `kitsune status` shows whether it is up. |
| "model 'x' is not installed" | Run `ollama pull x`. |
| Port 8788 is taken | A stale copy of this app is stopped automatically. If another program holds the port, start refuses to run rather than silently moving to another port. Free the port and start again. |
| Phone cannot connect | Same wifi? Do not start with `BIND=127.0.0.1`. The phone button in the app shows the address to use. |
| First reply is slow | The model loads on first use (30 to 60 seconds). `kitsune warm` loads it ahead of time. |
| Moved the folder | Run `bash install.sh` again so the command points to the new location. |
| Logs | `server.log` in this folder, or `tail -f server.log`. |

### Windows

`start.sh`, `install.sh` and the `kitsune` command are bash scripts, so on Windows they need Git Bash. `server.py` itself is plain Python and contains Windows handling for the terminal, so you can also run it directly with `python server.py` and open http://localhost:8788. The Windows path has had less testing than Linux, so expect rough edges and please report them.

---

## Privacy

Everything stays on your machine: bots, chats, knowledge files and settings are plain files in this folder, and the only network traffic is to your local Ollama at `http://localhost:11434`. The tunnel and the terminal are the two features that can widen access, and both are opt-in.
