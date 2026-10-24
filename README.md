# cubbie-berry: Group Cubbie

Team wildberry, DevHacks 2026.

**Group Cubbie** is a Discord bot for class study groups.

- It turns notes into Kahoot-style **Boss Battle** quiz games. You can play inside Discord with buttons, or scan a QR code and play on your phone against a big host screen.
- After each game, it tells the group which topics it's collectively weak on.
- It **connects to each student's personal Cubbie** (the iMessage AI):
  - Cubbie shares only what the student approves, so games target what the whole group needs.
  - Cubbie then turns group events into calendar entries, reminders and private drills.

## Two agents

| | Group Cubbie (Discord bot, Track 3) | Personal Cubbie (iMessage, Track 1 skill) |
|---|---|---|
| Sees | Group totals, game results | The student's Canvas, calendar, memory |
| Does | Builds decks, runs games, recaps, schedule polls | Shares an approved profile, picks up group updates, adds sessions to the calendar, sends private results and drills |

Cubbie can't receive incoming messages, so the bot leaves updates in a per-student inbox, and Cubbie checks it on a schedule the student approves. The full design is in [CLAUDE.md](CLAUDE.md).

## Set up the Discord bot (about 10 minutes)

1. **Create the app.** Go to <https://discord.com/developers/applications>, click **New Application**, and name it `Group Cubbie`. Add an icon and description on **General Information**.
2. **Get the token.** On the **Bot** tab, click **Reset Token** and copy it into `.env` as `DISCORD_TOKEN`. Never paste it in chat or commit it.
3. **Turn on intents.** Still on the **Bot** tab, under *Privileged Gateway Intents*, turn on **Message Content Intent**. `/quiz new from_chat` needs it to read recent messages.
4. **Make the invite link.** Go to **OAuth2 → URL Generator**:
   - **Scopes:** `bot` and `applications.commands`
   - **Bot permissions:** View Channels, Send Messages, Send Messages in Threads, Embed Links, Attach Files, Read Message History, Add Reactions, Use External Emojis, and Send Polls
5. **Invite it.** Make a test server (for example "CSE 230 study group" with a `#study` channel), open the generated URL, and add the bot.
6. **Get the server ID.** In Discord, turn on **User Settings → Advanced → Developer Mode**. Right-click the server, choose **Copy Server ID**, and put it in `.env` as `DISCORD_GUILD_ID`. This makes slash commands show up instantly.
7. **Run it.**
   ```
   pip install -r requirements.txt
   cp .env.example .env      # fill in the values
   cloudflared tunnel --url http://localhost:8000
   ```
   Put the `https://….trycloudflare.com` URL that cloudflared prints into `.env` as `PUBLIC_BASE_URL`, then run `python main.py`.

No AI key? Set `MOCK_LLM=true` and the whole demo runs on sample questions.

## Commands

| Command | What it does |
|---|---|
| `/help` | How everything works |
| `/setup` | Course, exam date and timer for this channel (needs Manage Server) |
| `/quiz new` | Build questions from a file, text, or recent chat |
| `/quiz play` | Start a game: **chat** (Discord buttons) or **arena** (QR + phones + host screen) |
| `/quiz stop` · `/quiz rematch` · `/quiz export` | Stop the game, rematch on weak topics, or export to Kahoot or Quizlet |
| `/pop now` · `/pop schedule` · `/pop off` | Text pop quizzes in the chat: answer by replying with a letter |
| `/course` | The course content the group's quizzes are built from (shared by members' Cubbies) |
| `/link` · `/unlink` | Connect or disconnect your personal Cubbie |
| `/me` | Your own results (private) |
| `/group status` · `/group schedule` | Group weak spots, and a poll for the next session |

## Track 1 Cubbie Skill: `group-chat-assistant`

The skill is in [`group-chat-assistant/`](group-chat-assistant/), and is the personal-Cubbie side of the link. It also works on its own as a solo quiz, or as a relay quiz for any group chat (paste the questions in, send Cubbie a screenshot of the answers).

**Install:** text Cubbie `https://github.com/dkoyi/cubbie-berry/tree/main/group-chat-assistant`

The skill needs no keys or packages. `cubbie.yaml` only declares the bot's server hosts.

## What the agents share and when they ask

- Before sharing anything, Cubbie lists the exact fields and waits for the student's yes. The script also drops any field outside a fixed allowlist.
- The bot posts only group totals. Each student's own results go only to their Cubbie, or to `/me`.
- Calendar events, reminders, check-ins and wake-up calls each need the student's yes.
- Before the recap posts, the bot asks the game host to confirm.
- `/unlink`, or texting Cubbie "leave the group", deletes the student's data from the server.
