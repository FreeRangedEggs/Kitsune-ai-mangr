# kitsune//ai-mangr

**Version 2.0.4** (since 1.0: setup wizard + feature switches, built-in text editor, six-part security hardening, and the `kitsune uninstall` command. Since 2.0.1: bash/zsh/fish-proof `kitsune` install + a copy-paste fix-it guide for the command. Since 2.0.3: `kitsune` checks which ollama models are installed - start, status and warm all report them and print the exact `ollama pull` command when one is missing. Since 2.0.4: the model picker in the chat menu stays live - it re-checks ollama every time you open it, so a model you just pulled shows up without a reload, and your pick is never silently reset.)

A private, local chat app for [Ollama](https://ollama.com) models. Make bots with their own personalities, talk to them from your PC or your phone, give them files to read, and keep every word on your own machine.

- **Zero dependencies.** The whole server is one plain `python3` file.
- **Fully local.** Chats, bots and files live in this folder. Nothing is sent anywhere.
- **One fixed address.** The app always answers on port `8788`, so a phone bookmark or home-screen icon never breaks.
- **Phone friendly.** Installable as a home-screen app, with a UI built for small screens.

---

## Quick start

Built for Linux. You need **Python 3** and **Ollama** with at least one model pulled (for example `ollama pull dolphin3:8b`). `kitsune` checks your installed models on start - if none are there, or a bot asks for a model you do not have, it prints the exact pull command to run.

```bash
bash install.sh      # one-time: puts the `kitsune` command in your PATH
kitsune              # start the app
```

If `kitsune` says `command not found` right after installing, that is just the terminal you are already in not knowing the new PATH yet. Run the line for your shell (or simply open a new terminal):

```bash
source ~/.bashrc                        # bash - the usual Linux shell
source ~/.zshrc                         # zsh
fish_add_path ~/.local/bin; exec fish   # fish
```

Still nothing? **[If the `kitsune` command does not work](#if-the-kitsune-command-does-not-work)** further down is a two-minute fix with copy-paste commands for every known cause.

Open **http://localhost:8788**, pick a persona, and talk. The first open runs a short setup wizard - pick your features and a look, or leave everything on.

Prefer not to install anything? From this folder, `bash start.sh` does the same thing.

---

## The `kitsune` command

`install.sh` adds a small launcher called `kitsune` to `~/.local/bin` and puts that folder on your PATH - in the rc file your shell actually reads: `.bashrc` for bash, `.zshrc` for zsh, `~/.config/fish/config.fish` for fish. Open a new terminal afterwards, or source that file in the one you have. If the command still refuses to work, the section **[If the `kitsune` command does not work](#if-the-kitsune-command-does-not-work)** below walks you through it with specific commands.

| Command | What it does |
| --- | --- |
| `kitsune` | Starts the app. If it is already running, it restarts it. |
| `kitsune stop` | Stops the app. |
| `kitsune status` | Shows whether the app is running, whether Ollama is reachable, every installed AI model with its size, whether the bots' models are among them, and what is in RAM. |
| `kitsune warm` | Starts the app and loads the model into RAM now, instead of on your first message. Refuses with the pull command if the model is not installed. |
| `kitsune warm <model>` | Same, but warms a specific model. |
| `kitsune tunnel` | Opens a temporary https link with a QR code, for use away from home. |
| `kitsune uninstall` | Removes the `kitsune` command again. Asks "are you sure?" first. |

Notes:

- Nothing is copied. The launcher points at this folder, so if you move the folder, run `bash install.sh` again.
- `bash install.sh --dir /some/folder` installs the launcher somewhere else.
- `kitsune uninstall` (or `bash uninstall.sh`) stops the app, removes the launcher and the PATH lines `install.sh` added, and then asks whether to delete the app folder too - it holds your chats, bots and settings, so that question defaults to no. `bash uninstall.sh --yes` skips the questions (scripted use). `bash install.sh --uninstall` does the same thing.
- Environment variables: `PORT=...` changes the port. Reaching the app from other devices is an explicit choice: `kitsune --lan`, the setup wizard question, or settings > app > "reach from other devices" (all write/flip the same switch; the default is this-PC-only `127.0.0.1`).

---

## If the `kitsune` command does not work

Every fix below is a command you can paste. Work through the steps in order - each takes seconds and tells you which step comes next.

**Step 1 - find out whether it is the command or the app:**

```bash
~/.local/bin/kitsune status
```

- It prints `[ai-mangr] running` or `[ai-mangr] not running` - the app is fine, only your PATH is missing. Do step 2.
- `No such file or directory` (no mention of start.sh) - the launcher was never written. `cd` into the app folder, run `bash install.sh` again, and read what it prints; its error says exactly what is wrong (no start.sh next to it, no permission, wrong folder). Then do step 2.
- `bash: /some/old/path/start.sh: No such file or directory` - the launcher points at a folder you moved or deleted. Do step 4.

**Step 2 - put `~/.local/bin` on your PATH (pick your shell):**

```bash
# bash - the usual Linux shell, and Git Bash on Windows
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# zsh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# fish
fish_add_path ~/.local/bin
exec fish            # restart fish so the change applies
```

Then check with `type kitsune` - it should print a path. If your terminal has been open a while, open a brand-new one instead: terminals only read their rc file at startup. zsh and fish never read `.bashrc`, so a PATH line that an older install put there (or in any file except your own shell's rc) does nothing for them - the commands above put it in the right file.

**Step 3 - still nothing? clean slate:**

```bash
cd /path/to/kitsune-ai-mangr      # the app folder
bash install.sh --uninstall       # answer y - removes launcher + PATH lines, keeps the app folder
bash install.sh                   # install again, watch for errors
```

Then a new terminal and `kitsune status`. This rewrites both pieces from scratch and clears out anything a half-finished install left behind.

**Step 4 - moved the folder? point the launcher at the new place:**

```bash
cat ~/.local/bin/kitsune          # the APP= line shows where it points now
cd /new/path/to/kitsune-ai-mangr
bash install.sh                   # rewrites the launcher with the new path
```

**Step 5 - the bypass that always works, even if every step above fails:**

```bash
bash /path/to/kitsune-ai-mangr/start.sh     # start the app straight from its folder
```

Open **http://localhost:8788**. Nothing is lost by skipping the `kitsune` command: everything it does is also `bash start.sh` (plus `stop`, `status`, `warm`) from that folder. You can retry the install any time.

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

Included persona:

| Persona | What it is |
| --- | --- |
| **Bot** | Plain default bot. Uses whatever model is picked in the chat menu. |

That is the whole shipped set on purpose: the app starts with just Bot, and every other persona is one you make, import, or drop into `bots/`.

### Persona packs

36 extra personas in six themed packs - furry-pack (with avatars), dim-harbor, neon-district, bramblewick, emberhold and stellar-diner - ship as a separate download, `kitsune-bot-packs.zip`, instead of inside the app folder. Import them from the bots menu (**import**, pick the `.ai` files) or the **+** button. Nothing is active until you import it, and a pack bot behaves like any other bot afterwards.

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
- **The model picker (top of the chat menu) is live:** it re-checks ollama every time you open it. Pull a model in a terminal, open the picker again, and it is there - no page reload. Your choice is remembered per bot, and a model that is not installed yet stays selectable, marked "not installed", and starts working the moment you pull it. Opening a different chat follows that chat's model; repainting the chat you are in never undoes your pick.
- Bots ticked in settings > app > the terminal run gate get a **>_ run** button under their code blocks: the command is always typed into the terminal first, in view, and nothing executes until you press run. (Needs the terminal on.)

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

## Setup wizard and features

The first time you open the app, a short setup wizard walks you through it: which parts of the app should exist (terminal, text editor, themes, music, chats menu, bot manager, phone pairing, the settings gear), and how it should look. It re-runs itself only if you wipe those settings. To open it again later, add `#setup` to the address bar.

Every part it asks about is a **feature switch** - a line in `config/settings.conf` like `feature_terminal off`. Each one hides that part of the UI *and* turns off its API. Turn everything off except `feature_chats` and you get the raw chat gui: pick a bot, send messages, nothing else. A lock-screen for the app is impossible by design: the wizard (and `settings > features`) is always reachable.

## Built-in text editor

The pencil icon in the top bar opens a small text editor. Pick a bot, then pick a file: the bot's own `.ai` definition (name, description, greeting...) or one of its knowledge files. Edit and save. A save that would break the bot file is refused, and every save keeps a one-shot `.<file>.edit-bak` next to the original. Knowledge file rows in the bot form have an **edit** button too. The editor is a feature like any other - `feature_editor off` removes it completely.

---

## Settings and themes

The gear button has three sections:

- **This device:** text size, message width, compact spacing, enter-key behaviour. Stored in this browser only, so phone and PC can differ.
- **Theme:** 12 presets (fox, amoled, light, catppuccin, gruvbox, dracula, neon-nights, sunset-strip, candy-pop, deep-space, sakura, toxic-green), a color picker for every color, font, base text size and bubble roundness. It previews live. Cancel undoes it, and save writes `config/theme.conf` so every device gets the same look.
- **App:** one-model-at-a-time mode, the PIN lock, the terminal switch, the terminal's per-bot run gate, and the "reach from other devices" LAN switch (all in `config/settings.conf`). The **features** section here flips the same switches the setup wizard asks about.

**One model at a time** (`single_model on`) unloads every other model from RAM before each reply, so two models never share your memory. Useful on 8 GB machines.

You can also edit `config/theme.conf` by hand. Save and refresh the browser. Presets are included as commented blocks at the bottom of the file.

---

## PIN lock (optional)

Set a PIN in settings, App, and every page and API call needs an unlock on every device.

- Only a salted hash is stored. The PIN itself is never written down.
- Minimum 6 characters, compared in constant time.
- Unlocking gives the device a session cookie for 7 days (HttpOnly, SameSite=Strict, Secure over https). Restarting the server signs everyone out.
- 5 wrong tries from one IP means a 30 second wait.

**Locked out?** Stop the server, delete the `pin_hash`, `pin_salt` and `pin_iters` lines from `config/settings.conf`, and start again.

The app speaks plain http on your wifi, so this is casual protection. It keeps flatmates and guests out of the UI, but it does not encrypt traffic. It listens on `127.0.0.1` (this PC only) unless you turn on "reach from other devices"; pair that with a pin, or use the tunnel for https.

---

## Web terminal (optional, off by default)

A small console and file browser that runs on the machine hosting the server, like ssh from the browser. Open it from the bots menu (`>_ terminal`) or settings, App. The switch at the top of the panel turns it on.

- It only answers the machine's own browser (`127.0.0.1` / `::1`) - phones over LAN or the tunnel are refused, and so is anything whose request carries a proxy header (`X-Forwarded-For`, `CF-Connecting-IP`, `Cf-Ray`), because tunnel traffic also arrives from localhost.
- It cannot be turned on until a PIN is set, and removing the PIN locks every command out again.
- **Console:** one command at a time, output capped, killed after 120 seconds. Your working folder is remembered, so `cd`, `cd ~`, `cd ..` and `cd -` work, and the prompt shows where you are. Quick buttons run Windows commands on a Windows host and Linux commands elsewhere. Interactive programs (vim, a Python REPL) do not work.
- **File browser and editor:** reaches your home folder plus this project. Edits keep a `.term-bak` copy of the old file. `server.py` and `index.html` are write-locked here on purpose. Each file row has an **import** button that copies it into the open bot's knowledge, and a dropdown picks which bot receives it without switching chats.

> **Security: read this.** While the terminal is on, anyone using this machine's browser can run anything on that machine. Keep it off when you do not need it, keep the PIN set (every terminal command and the turn-on switch need it), and **never expose the app to the public internet with the terminal on.**

---

## Music player

The note button plays a shuffle of the songs in your `~/Music` folder (subfolders count as albums). Play, skip and volume are all there is. Closing the panel keeps the music going, and the button glows while something plays.

Formats are whatever your browser can decode (mp3, m4a, ogg, opus, flac, wav, webm). Up to 2000 songs per scan. It is read-only and locked inside the Music folder.

---

## Files in this folder

```
server.py        the whole server (plain python3, no dependencies)
index.html       the UI, sits right next to server.py
start.sh         start / stop / status / warm / uninstall
install.sh       puts the `kitsune` command in your PATH
uninstall.sh     removes it again (asks "are you sure?" first)
tunnel.sh        temporary https link + QR for away from home
sw.js            service worker (needed for "add to home screen")
bots/            your personas, one .ai file each (ships with just Bot)
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
| `kitsune: command not found` | Run the line for your shell from quick start (`source ~/.bashrc`, `source ~/.zshrc`, or `fish_add_path ~/.local/bin; exec fish`), or open a new terminal. Still broken? Follow **[If the `kitsune` command does not work](#if-the-kitsune-command-does-not-work)** above, starting at step 1: `~/.local/bin/kitsune status`. |
| `bash: .../start.sh: No such file or directory` when running `kitsune` | The launcher points at a folder you moved or deleted. `cat ~/.local/bin/kitsune` shows where it points; `bash install.sh` from the new folder fixes it. |
| `python3: command not found` (or start fails with no python) | start.sh falls back to `python` on its own, so this means neither name is installed. Install Python 3 (Windows: python.org installer, tick "Add python.exe to PATH"), then open a new terminal. |
| "ollama is not reachable" | Start it with `ollama serve`. `kitsune status` shows whether it is up. |
| "model 'x' is not installed" | Run `ollama pull x`. `kitsune status` lists every model that IS installed, and start/warm print the exact pull command when a bot asks for one you do not have. |
| A model I pulled does not show in the picker | Open the model picker again - it re-checks ollama every time it opens, so new models appear without a page reload. (The list also refreshes when you come back to the tab.) |
| Port 8788 is taken | A stale copy of this app is stopped automatically. If another program holds the port, start refuses to run rather than silently moving to another port. Free the port and start again. |
| Phone cannot connect | Same wifi? Turn on "reach from other devices" (settings > app, or `bash start.sh --lan`) and restart. The phone button in the app shows the address to use. |
| First reply is slow | The model loads on first use (30 to 60 seconds). `kitsune warm` loads it ahead of time. |
| Terminal will not turn on | A PIN must be set first (settings > app). It also only answers this PC's own browser - phones over wifi and tunnel traffic are refused on purpose. |
| The setup wizard reappears | It auto-opens only while `config/settings.conf` has no `installer_done on` line; finishing the wizard sets it. Re-open it on purpose with `#setup` in the address bar. |
| Removing the app | `kitsune uninstall` (or `bash uninstall.sh`). It asks "are you sure?" first, then whether to delete the app folder too. |
| Moved the folder | `kitsune` errors with the old path, or phones/bookmarks stopped working. Run `bash install.sh` again from the new folder so the command points there. |
| Logs | `server.log` in this folder, or `tail -f server.log`. |

### Windows

`start.sh`, `install.sh` and the `kitsune` command are bash scripts, so on Windows they need **Git Bash**: open this folder in Git Bash, run `bash install.sh`, then close and reopen Git Bash and type `kitsune`. If it still says `command not found`, run the bash block of step 2 in **[If the `kitsune` command does not work](#if-the-kitsune-command-does-not-work)** - it is the same on Git Bash.

The server itself is started with `python3` if that exists and falls back to `python` automatically, so either name works. If Git Bash says neither exists, run the [python.org](https://www.python.org/downloads/) installer and tick **Add python.exe to PATH**, then reopen Git Bash. `server.py` is plain Python and contains Windows handling for the terminal, so you can also skip the launcher entirely: `python server.py`, then open http://localhost:8788. The Windows path has had less testing than Linux, so expect rough edges and please report them.

---

## Privacy

Everything stays on your machine: bots, chats, knowledge files and settings are plain files in this folder, and the only network traffic is to your local Ollama at `http://localhost:11434`. The tunnel and the terminal are the two features that can widen access, and both are opt-in.

Hardening that ships with 2.0: the server binds to `127.0.0.1` unless you explicitly turn on "reach from other devices", and it prints a warning at startup when the app is network-reachable without a PIN. Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer` (a strict no-inline-script content-security-policy is still work-in-progress). State-changing requests (post/put/delete) must match the app's own origin, so other websites cannot drive it from your browser. The terminal refuses anything that is not this PC's own browser - phones over wifi and tunnel traffic included.
