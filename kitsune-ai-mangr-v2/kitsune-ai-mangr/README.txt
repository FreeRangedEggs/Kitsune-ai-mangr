kitsune//ai-mangr v2 - quick start
==================================

1. put this folder anywhere you like (example: ~/.server)
2. bash start.sh          -> web app on http://localhost:8788
3. open it, tap a bot, talk. everything stays on your machine.

--- your one address (the phone part) ---

the port is FIXED at 8788 and never changes - that's the feature.
the app always answers on the same address, so your phone bookmark or
home-screen icon never breaks.

  bash start.sh prints the address, e.g.:

    on this pc : http://localhost:8788
    from phone : http://192.168.1.23:8788   <- your one address

even easier: open the app on the pc and tap the PHONE BUTTON (top right).
it shows the address(es) plus a QR code - point your phone camera at it.

make it a phone app (once, 20 seconds):
  android: chrome -> open the address -> menu (3 dots) -> "add to home screen"
  iphone : safari -> open the address -> share -> "add to home screen"
from then on it opens like an app, full screen, no typing. ever.

tips for a truly stable address:
  - your router hands out LAN ips; ask it to keep yours reserved
    (dhcp static lease), OR
  - use the hostname form the phone menu also offers:
    http://<your-pc-name>.local:8788  - survives ip changes on
    iphone/android/most linux desktops (mDNS).

port taken by another program? a stale copy of this app is stopped
automatically. a foreign program keeps the port, and start REFUSES to
run rather than silently hopping to 8789 (a moving address is what used
to break phone bookmarks). it tells you what to do instead.

private by default? the server listens on your LAN so the phone can
reach it. to lock it back to this pc only:
  BIND=127.0.0.1 bash start.sh     (phone + tunnel stop working)

--- files in this folder ---

  server.py     the whole server - plain python3, zero dependencies
  index.html    the ui - lives RIGHT NEXT TO server.py
  start.sh      start / stop / status / warm-model
  tunnel.sh     temporary https link for away-from-home (QR in terminal)
  config/
    theme.conf    kitty-style theme config: edit a line, save, refresh
                  the browser. presets (catppuccin/gruvbox/dracula) are
                  commented out at the bottom of the file
    settings.conf app switches - the gear button writes it. single_model
                  on = before each reply every other loaded model is
                  dropped from ram, so two models never share your 8gb
  robot.png     the robot chip used by the bots-menu buttons
  logo.jpg      the fox logo (topbar + welcome screen + icons)
  icon-192.png  pwa icons for "add to home screen"
  icon-512.png
  avatar.png    the default profile picture for bots (swap it freely)
  .port         the port the server actually bound - written at boot,
                removed on shutdown, read by tunnel.sh
  sw.js         service worker (needed for "add to home screen")
  bots/         one .ai file per bot - see bots/README.txt
  chats/        chat history, one json file per chat
  avatars/      bot icons picked in the ui land here

older installs kept theme.conf / settings.conf next to server.py -
the server tucks them into config/ automatically on the first boot.

--- what's new in v2 ---

  - one fixed address: port never drifts, LAN access built in, QR in the ui
  - server.py slimmed down (the whole ui is no longer duplicated inside it)
  - code blocks + inline code render in chat (great with coder models)
  - copy button under every bot reply, export a chat as markdown
  - duplicate a bot with one tap (bots menu, the double-arrow)
  - paste screenshots / drag-drop images straight into the chat
  - enter-key behavior switch in settings (multiline typing on phones)
  - friendlier errors: "ollama is not reachable - start it with: ollama
    serve", "model 'x' is not installed - run: ollama pull x"
  - smoother streaming on phones (renders per screen frame, not per token)
  - mobile keyboard fixes, scroll-to-bottom chip, esc closes menus

--- bot .ai format (plain text, edit in vim, refresh to apply) ---

  name: "Aria"
  description: "who she is, how she talks"
  greeting: "*looks up* Sit by the fire."
  color: "#d4a373"
  model: "dolphin3:8b"
  temperature: "0.9"
  max_tokens: "400"
  icon: "avatars/aria-icon.png"

(see bots/README.txt for the full field list)

chat controls: under your last message -> edit / delete.
under the bot's last reply -> copy / redo / continue.
send becomes stop while a reply is streaming.

--- pictures (vision models) ---

the paperclip next to the input box attaches photos - up to 4 per
message, auto-shrunk to 1280px so phone pics stay light. you can also
paste (ctrl+v) or drag them in. the button only shows when the picked
model can actually see (llava, minicpm-v, moondream, gemma... - ollama
reports this itself). dolphin3 and most text models are blind, so
nothing changes for them: the server strips the pictures before they
reach a blind model, and keeps them saved in the chat for when you
switch back to a vision one.
