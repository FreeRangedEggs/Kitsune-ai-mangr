this folder is where the server scans for bots - one .ai file per bot.
drop a file in here and it appears in the app (refresh the page).

the format is plain text, quotes optional:

  name: "Aria"
  description: "who she is, how she talks - becomes the system prompt"
  greeting: "*looks up* Rough night to be out. Sit by the fire."

  color: "#d4a373"
  model: "dolphin3:8b"

  temperature: "0.9"
  max_tokens: "400"

  icon: "avatars/aria-icon.png"

notes:
- name, description, greeting are what matter. everything else is
  optional (color defaults fox orange, model defaults to the chat picker)
- temperature: creativity, 0 = rigid and predictable, 1 = normal,
  1.5+ = chaotic. max_tokens: cap on reply length (default unlimited)
- icon: a png/jpg picture for the bot. a bare filename ("aria.png") is
  looked up next to server.py and in avatars/; "avatars/aria.png" (what
  the bot creator in the ui writes) points straight into avatars/.
  old files with avatar: still work - same thing (if a file lists
  both, the last one wins).
  no icon key (or file missing) = the default avatar.png that ships
  with the app. swap that file to change every bot's fallback at once
- a line that is NOT "key: value" continues the field above it,
  so multi-line descriptions and greetings just work
- blank lines are ignored, use them to space things out
- lines starting with # before the first field are comments
- empty folder = no bots. make one with the UI ("+ new bot") or
  save a file like the one above as something.ai in here

want a bot that sees your pictures?
- give it a vision model, e.g. model: "minicpm-v" or "llava:7b"
  (ollama pull minicpm-v first). with a vision model on the bot the
  paperclip button lights up in the ui and you can attach photos
- free coding brains for a code-helper bot: model: "qwen2.5-coder:7b"
  (best fit for 8gb ram), "qwen2.5-coder:3b" (faster), or
  "deepseek-coder:6.7b". every bot can have its own model

sharing bots (the poor man's marketplace):
- export button in the bots menu downloads the current bot's .ai file
- import button loads .ai files from your device (pick several at once)
- the url button installs straight from a link - point it at a raw
  .ai file on github gist / a repo / your own host and it lands here
- the double-arrow button in the bots menu duplicates a bot
- a friend exports Aria.ai, you import Aria.ai: same bot, same vibe
