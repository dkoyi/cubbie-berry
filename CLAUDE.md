# CLAUDE.md — Group Cubbie (DevHacks 2026 · Cubbie Track 3: Group Chat Assistant)

You are building a hackathon project with team **wildberry** (Malaika, Dhanush, Sashikant, Apoorv).
**Hard deadline: Sunday Oct 25, 2026, 12:00 PM (America/Phoenix).** Judging runs 2:00–4:30 PM.
Optimize for **a working, impressive live demo**. It should feel as solid as a popular Discord bot.

---

## 1. What we're building

**Group Cubbie** is a Discord bot for class study groups. It turns notes into Kahoot-style **Boss Battle** quiz games and tells the group what it's collectively weak on. It also **connects to each student's personal Cubbie** (the iMessage AI), using our Track 1 skill in [group-chat-assistant/](group-chat-assistant/).

There are two agents:

| | Group Cubbie (this repo) | Personal Cubbie (each student's iMessage) |
|---|---|---|
| Lives in | The Discord study channel | The student's 1:1 iMessage thread |
| Knows | Group aggregates, game results | The student's Canvas, calendar and memory |
| Does | Builds decks, runs games, recaps, schedule polls | Shares an approved profile; turns group events into calendar entries, reminders, wake-up calls and private drills |

We use **one bot per group chat**, and each student links their own account. Several Cubbies in one chat isn't possible (Cubbie can't join groups), and it would be noisy and leak data anyway.

**The "we need this" moment:** the bot already knows three of four members are weak on cache associativity and the midterm is Thursday. So the boss is *weak to* that topic and the game drills it. The recap tells the group what it missed. Each person's own Cubbie then privately texts them their breakdown, adds the next session to their calendar, and offers a drill. Track 3 asks teams to show **what agents share, how they handle conflicting constraints, and when they ask for confirmation**. That's covered in section 5, phase 7.

---

## 2. How the bot and Cubbie connect (read before coding)

```
 Student's iPhone (iMessage)               Our server (one Python process)            Discord study channel
 ┌───────────────────────────┐  HTTPS     ┌───────────────────────────────┐           ┌───────────────────────┐
 │ Personal Cubbie           │ ─────────► │ Link API  /api/link           │           │ Group Cubbie bot      │
 │  + group-chat-assistant   │  push      │           /api/member         │ ◄───────► │  slash commands,      │
 │    skill (groupsync.py)   │  profile   │ Per-member INBOX ◄── bot      │  shared   │  buttons, polls,      │
 │                           │ ◄───────── │  queues session/results/nudge │  memory   │  chat-mode game       │
 │  scheduled check-in pulls │  pull      │ Game engine + WebSockets      │ ◄──────── │                       │
 └───────────────────────────┘  inbox,    └───────────────────────────────┘ phones    └───────────────────────┘
                                results            /host/{code}  /play/{code}  scan QR (Arena mode)
```

- **Cubbie can't receive calls.** Nothing can push to Cubbie, so every exchange starts on Cubbie's side:
  - **push:** `join` / `update` the profile, when the student approves.
  - **pull:** `results`, when the student asks "how did I do?".
  - **pull:** `inbox`, through a daily scheduled check-in the student approved, or when they ask "any group updates?".
- **Bot → Cubbie goes through the inbox.** The bot appends messages to `Member.inbox`, and Cubbie picks them up and acts on them. The kinds are:
  - `session`: Cubbie offers to add it to the calendar, set a reminder, or make a wake-up call.
  - `results`: Cubbie sends the private breakdown and a drill.
  - `nudge`: one practice question.
  - `deck`: Cubbie offers a warm-up.
  - `pack_request`: the bot asks for a Canvas unit it doesn't have. Cubbie asks the student before sharing.
- **Cubbie is the course-content source.** The bot has no Canvas access. A linked student's Cubbie pushes a **course pack** (`PUT /api/course-pack`):
  - the unit outline with topics and summaries,
  - upcoming assessments and the topics they cover,
  - ≤10 short quoted excerpts with sources.
  
  It never includes grades, submissions, or open graded assignments and their answers. The bot generates every quiz from the pack (plus any uploaded notes), so questions match *this* class's content and exam schedule. When a `/quiz new` topic isn't in the pack, queue a `pack_request` to linked members and fall back to uploaded notes or chat in the meantime.
- **Everything time-critical stays in Discord.** "The game starts now" goes in the channel with @mentions, not the inbox. Inbox items are for things that matter hours later.
- **The game never depends on Cubbie.** Every command works with zero linked members. Linking only personalizes. If the link API errors, log it and carry on.
- **The member token is the only identity.** Only the student's Cubbie holds it, in their sandbox.
- **The API must match `group-chat-assistant/scripts/groupsync.py` exactly.** If you change one, change both.

---

## 3. Stack (do not change without asking)

- **Python 3.11+**, with **one process**: FastAPI, plus the discord.py bot started as an asyncio task in the lifespan, so they share in-memory state.
- **Discord:** `discord.py` 2.x, using app commands, `ui.View` buttons, selects and modals, and native polls.
- **Server:** `FastAPI` + `uvicorn[standard]` WebSockets.
- **LLM:** the `anthropic` SDK, with the model from `LLM_MODEL` (default `claude-sonnet-5-5`). All calls go through `llm/client.py`. `MOCK_LLM=true` must run the whole demo with no key.
- **Files:** `pypdf` for PDFs, `qrcode[pil]` for QR PNGs, and `openpyxl` for the Kahoot export.
- **State:** in-memory dicts plus a JSON snapshot in `data/state.json` on every change, reloaded at startup so a restart mid-demo loses nothing. **No database.**
- **Arena frontend:** plain HTML/CSS/JS with no build step, plus these libraries from **cdnjs/jsDelivr with exact versions**:
  - `gsap@3.12.5`, including the Flip plugin, for all motion
  - `canvas-confetti@1.9.3`
  - `qrcode` is server-side only
  - sounds are synthesized with the Web Audio API, so there are no audio files and no licensing questions
- **Public URL:** `cloudflared tunnel --url http://localhost:8000` (→ `*.trycloudflare.com`) or Render (`*.onrender.com`). Those are the **only** hosts the Cubbie skill may call, so don't use ngrok.

---

## 4. Discord UX standards (what makes it feel like a real bot)

- **Answer within 3 seconds.** Anything slow (LLM, PDF) calls `interaction.response.defer(thinking=True)`, then edits a progress embed: "📄 Reading notes… → ✍️ Writing 10 questions… → ✅ Ready".
- **Ephemeral for anything personal:** errors, link codes, your own stats, confirmations. Public only for group content.
- **Use buttons, selects and modals rather than typed arguments** wherever possible. Use **persistent views**: `timeout=None`, stable `custom_id`s like `gc:join:{code}`, and `bot.add_view(...)` at startup, so old buttons work after a restart.
- **One brand style** in `bot/embeds.py`: one accent color, a 🐻 Group Cubbie footer, and consistent emoji (📚 deck, ⚔️ game, 📉 weak spots, 🔗 link, 📅 schedule). Draw progress bars as text: `▰▰▰▰▱▱▱▱▱▱ 40%`.
- **Permissions:** `/setup` and `/quiz stop` need Manage Server *or* being the game host. Use `@app_commands.guild_only()` everywhere.
- **Cooldowns:** `/quiz new` 1 per 30s per channel, `/link` 1 per 60s per user. When a cooldown hits, reply with a friendly ephemeral message that includes the seconds left.
- **Guard rails:**
  - one active game per channel ("A game is running, join it or `/quiz stop`"),
  - attachment type and size checks (PDF/TXT/MD, ≤10 MB),
  - answer clicks after the deadline get an ephemeral "too late".
- **A global error handler** (`tree.on_error`) logs the trace and sends "Something broke on my side. Try again in a moment." **Never post stack traces in chat.**
- **Rate limits:** throttle live message edits to ≤1 per 1.5s (answered counters), and batch updates.
- **Autocomplete** for the `focus` topic and `mode` options.
- **First-run experience:** when the bot joins a server, post a welcome embed with a **Set up** button that opens the `/setup` modal.

### Command set

| Command | Who | What it does |
|---|---|---|
| `/help` | anyone | An embed with categories and buttons. "How linking works" explains the Cubbie flow. |
| `/setup` | Manage Server | A modal for course code, exam date and default timer. Binds this channel as the group. |
| `/quiz new [file] [text] [from_chat] [questions:5–15] [focus]` | anyone | Builds the deck with progress updates, then shows the topics with **▶ Play (Chat)**, **📱 Play (Arena)**, **📤 Export** and **🔁 Regenerate** buttons. |
| `/quiz play [mode: chat\|arena] [timer: 10\|20\|30]` | anyone | Starts a game from the channel's deck. |
| `/quiz stop` | host / mod | Ends the game and posts the partial recap. |
| `/quiz rematch` | anyone | Builds a new deck from the last game's weak topics only. |
| `/quiz export format:kahoot\|quizlet` | anyone | Kahoot: a `.xlsx` in its spreadsheet-import format. Quizlet: a `.txt` of `question<TAB>answer` lines. Both come with 3-step import instructions, plus the tip that a linked Cubbie can do the import in its browser ("text your Cubbie: put our quiz on Kahoot"). |
| `/pop now [topic]` | anyone | One text pop quiz right now. |
| `/pop schedule [every: 1h\|2h\|4h] [quiet_from] [quiet_to]` · `/pop off` | Manage Server | Random pop quizzes in the channel during active hours. |
| `/course` | anyone | Shows the course pack the group is using: units, upcoming exams, who shared it, and when. |
| `/link` | anyone | Ephemeral code plus instructions to text it to your Cubbie. Also has a **Done** button that checks whether linking succeeded. |
| `/unlink` | anyone | Removes your profile (with a confirm button). |
| `/me` | anyone | Ephemeral: your last results and weak topics (works without Cubbie). |
| `/group status` | anyone | Linked count, aggregate weak spots, soonest exam. Never shows per-person data. |
| `/group schedule` | anyone | A native Discord poll of the 3 best overlapping free slots. When it closes, it queues `session` inbox items. |

---

## 5. Features, in build order (each phase ends runnable)

### Phase 1: Skeleton + bot framework (1 h)
- `main.py` starts FastAPI and the bot. It serves `/static`, `/host/{code}` and `/play/{code}`.
- Set up `bot/embeds.py`, the global error handler, `/help`, `/setup`, the welcome embed, and persistent-view registration.
- ✅ The bot is online, `/help` looks polished, and `localhost:8000/host/TEST` loads.

### Phase 2: Deck generation (1.5 h)
- `/quiz new` reads the **group's course pack first**: excerpts for grounding, units for topic tags, and `upcoming` for what's on the next exam. It then adds the attachment, the text, or the last 50 channel messages (`from_chat`), and any linked members' `notes_excerpt`s. Every question cites its source (for example "Lecture 9, slide 12"), and the reveal shows that source.
- The LLM generates N questions as strict JSON covering 3–5 topics. Validate, retry once, then fall back to the sample deck.
- **Personalize from aggregated linked profiles:** about 50% on the most common `weak_topics`, about 30% on the soonest exam, and about 20% review. The deck embed says why: "Focused on caches, which 3 of you marked as weak · midterm in 5 days."
- ✅ Test with `sample_notes.md`, with `MOCK_LLM=true`, and with `scripts/fake_link.py`.

### Phase 3: Chat mode game, played inside Discord (2 h). Build this first; it's the guaranteed path.
- The bot posts a **question embed** with the boss HP bar, topic, timer (`<t:unix:R>` countdown) and the question. It has **4 buttons**, one per Discord button style: 🔵 A primary, ⚪ B secondary, 🟢 C success, 🔴 D danger.
- A click gets an ephemeral reply: "🔒 Locked in B". One answer per person. The embed shows "7 answered" (throttled).
- At the deadline, or once everyone has answered, the embed **is edited into the reveal**:
  - the correct answer is ✅'d,
  - per-choice text bars,
  - "💥 −64 HP" with the new HP bar,
  - the top 3,
  - buttons disabled.
- After a 4s pause, the next question comes up.
- **Rules:**
  - Damage = `10 + speed_bonus(0–5)`. A correct answer on a `boss_weakness` topic is a **critical hit** (×2).
  - Streaks of 3 or more get a 🔥.
  - If fewer than 50% answer correctly, the **boss counterattacks** (a red embed).
  - The last question is **FINAL BLOW** (×2).
  - `boss_max_hp ≈ total_q * players * 0.7 * 12`, where players = whoever answered question 1.
- ✅ A full game with 2–3 accounts, or with a `scripts/fake_players.py` that simulates clicks through the engine directly.

### Phase 3.5: Text pop quizzes (1 h)
- The bot posts a plain message:
  `⚡ POP QUIZ · caches · 60s` + the question + `A) … B) … C) … D) …` + `Reply with a letter.`
- It listens with `on_message` (needs the **Message Content intent**) in that channel only, for the 60s window:
  - It accepts `^\s*\(?([abcd])\)?\b` (case-insensitive) from any member, first reply per person only.
  - It reacts 🔒 to each counted reply. It doesn't reveal anything.
  - It ignores bots and other chatter.
- At the deadline it posts the reveal: the answer, who got it (opted-in names, otherwise just a count), the one-line explanation with source, and a streak shout-out.
- Results feed the same per-topic stats as games, so `/me`, the recap and Cubbie's results all include pop quizzes.
- **Scheduling:** `/pop schedule` picks random times inside active hours. It skips a slot if the channel is mid-game, or if the last pop quiz got zero answers twice in a row (that's back-off, not spam). It prefers weak topics and whatever is on the soonest exam.
- **Stretch:** short-answer pop quizzes graded by the LLM ("Explain a TLB in one sentence").
- ✅ `/pop now` works with 2 accounts, and a schedule fires within 1 minute when set to a short test interval.

### Phase 4: Group recap (1 h)
- Per-topic group accuracy. Weak topics are below 60%, worst first.
- The LLM writes an explainer (≤80 words, one analogy) plus a practice question for the top 1–2 weak topics.
- The recap embed shows:
  - 🏆 the result and podium (opted-in names only),
  - 📉 "The group struggled with…",
  - 💡 the explainer,
  - **▶ Rematch weak topics**, **📅 Schedule next session** and **📤 Export** buttons,
  - the footer "🔗 Linked? Text your Cubbie 'how did I do?'".
- Save each linked player's per-topic results to `Member.results`, and queue a `results` inbox item.
- ✅ The recap posts within 5s of the game ending.

### Phase 5: Cubbie link API + inbox (1.5 h). This is the two-agent piece.
- **`/link`** creates a single-use code `ABCD-1234` (15 min, tied to channel and user). The ephemeral reply is:
  `Text your Cubbie: link my study group ABCD-1234 {PUBLIC_BASE_URL}`
  plus a **Done** button and a **What gets shared?** button.
- **API (`game/api.py`).** Every endpoint returns JSON; errors are 4xx `{"error": "..."}`.
  - `POST /api/link` `{code, profile}` → `{group_id, group_name, member_token, members_linked}`. 404 for an unknown code, 410 for an expired or used one. `group_id = str(channel_id)`.
  - `PUT /api/member` (Bearer) `{profile}` → `{ok}`
  - `GET /api/member/results` (Bearer) → `{group, games:[{date, score, rank, per_topic:{topic:[right,total]}, weakest}]}`. **Only this member's results.**
  - `GET /api/member/inbox` (Bearer) → `{messages:[{id, kind, at, text, ...}]}`. Messages are removed once returned.
  - `PUT /api/course-pack` (Bearer) `{pack}` → `{ok, version}`. The pack is merged into the group's pack by unit title, with newer units winning. Record who shared it and when. Server-side, apply the same caps as `clean_pack` in groupsync.py.
  - `GET /api/member/deck` (Bearer) → `{course, topics, questions:[{prompt, choices, answer_index, explanation, topic, source}]}`, the group's current deck, so Cubbie can put it on Kahoot or Quizlet.
  - `DELETE /api/member` (Bearer) → deletes the profile, results and inbox, and returns `{ok}`. Units the member shared stay in the group pack unless they ask for removal.
  - Validate profiles server-side against `MemberProfile` and drop unknown keys.
- When a profile arrives, post "🔗 **Dhanush** linked their Cubbie · 3/4 members linked". Never post the profile's contents.
- **Inbox producers:**
  - recap → `results`
  - closed schedule poll → `session` `{when, where, course}`
  - `/quiz new` → `deck` `{topics, exam}`
  - an optional daily nudge → `nudge` `{question, choices, answer_index, explanation, topic}`
- ✅ `scripts/fake_link.py` links 3 sample profiles and reads the inbox. `/group status` shows aggregates. A real Cubbie link works through the tunnel.

### Phase 6: Arena mode, the Netflix-party / Kahoot look (3 h)
- `/quiz play mode:arena` posts a QR code linking to `{PUBLIC_BASE_URL}/play/{code}`, plus a **🖥 Open host screen** link button. The host screen goes on the projector.
- WebSocket `/ws/{code}?role=host|player&name=...&u=<discord_user_id?>`. The JSON protocol:
  - `lobby {players}`
  - host `start`
  - `question {index,total,prompt,choices,topic,deadline_ms,weakness}` (never send `answer_index` early)
  - player `answer {choice}`
  - `answered_count {n,total}`
  - `reveal {answer_index,explanation,per_choice_counts,damage,crit,boss_hp,leaderboard,counterattack}`
  - host `next`
  - `ended {leaderboard,boss_defeated}`
- Both modes share **one engine** (`game/engine.py`). Only the transport differs.
- **`host.html` (projector, dark, big type):**
  - **Lobby:** the QR code, names popping in with a GSAP `back.out` stagger, and a pulsing "waiting for players" label.
  - **Question:** the card slides in, the 4 answer tiles use Kahoot-style colors *and* shapes (▲ ◆ ● ■, so colorblind players can tell them apart), there's an SVG countdown ring, and a tick sound plays in the last 5s.
  - **Boss:** a big emoji/CSS boss that bobs while idle. Its "weak to: <topic>" badge glows on matching questions.
  - **Reveal:**
    - wrong tiles fade and the right one scales up,
    - per-choice bars grow,
    - damage numbers float up from the boss,
    - the boss shakes and the HP bar drains with easing,
    - a **crit** adds a white flash and a "CRITICAL!" stamp,
    - a **counterattack** adds a screen shake, a red vignette and a low thud.
  - **Leaderboard:** rows reorder with GSAP Flip.
  - **End:** the boss explodes into confetti on victory, or laughs on survival. Then a podium reveal (3rd → 2nd → 1st).
- **`play.html` (phone, iPhone Safari first):**
  - name entry with a "show my name on the leaderboard" checkbox,
  - 4 giant shape and color buttons, each ≥64px tall,
  - haptic `navigator.vibrate` where supported,
  - a "locked in" screen, then ✅/❌ with the damage dealt and 🔥 streak.
  - Reconnecting with the same name restores the player's score.
- Respect `prefers-reduced-motion`, and disable shakes and flashes when it's set.
- ✅ 3 phones or tabs play a full game, and it looks great on a projector.

### Phase 7: Privacy, conflicts, confirmation (45 min, Track 3 points)
- **What's shared:**
  - Cubbie sends only the fields the student approved, and the script whitelists them.
  - The bot shows only aggregates.
  - Individual results go only to that student's Cubbie (by token) or to `/me` (ephemeral).
- **Conflicts** (demo at least one):
  - *Different exam dates:* the deck weights the soonest exam, and says so.
  - *Free slots:* `/group schedule` offers the overlaps. If there's no full overlap, it offers the slot that fits the most people and says "fits 3/4", without naming who can't make it.
  - *Opt-outs:* a member who shared no weak topics still plays.
- **Ask before acting on the group:** before posting the recap, ephemerally ask the host "[Post] [Edit] [Skip]", and auto-post after 30s.
- Explain all of this in the README under "What the agents share and when they ask".

### Phase 8: Stretch, in order
1. **Kahoot + Quizlet export** (45 min, `export/kahoot.py`, `export/quizlet.py`).
   - **Kahoot:** write the deck into Kahoot's spreadsheet-import template. Questions are ≤120 characters and answers ≤75 characters; shorten them with the LLM if needed. Time limits come from Kahoot's allowed set. **Download the current template from Kahoot's "Import spreadsheet" page, copy its exact layout, and fill a copy of it**; don't guess the columns.
   - **Quizlet:** write `question<TAB>correct answer` lines for Quizlet's Import box.
   - As far as we know, neither platform has a public API for creating content. So the bot hands over files, and a linked **Cubbie can do the upload in its own browser** for the student (see the skill's group-link.md).
   - Games played on those platforms don't feed our recap or Cubbie, so they're a bonus, not the main mode.
2. A daily 9 PM nudge in the channel, plus a `nudge` inbox item.
3. `/teachback`: the bot asks someone to explain the weakest topic, then grades the explanation and fills the gaps.
4. **Discord Activity:** embed the Arena *inside* a Discord voice channel using the Embedded App SDK. This is the true Netflix-party feel, but it needs OAuth and URL-mapping setup, so only attempt it if everything else is done.

---

## 6. File structure (repo root)

```
cubbie-berry/
├── CLAUDE.md  README.md  requirements.txt  .env.example  main.py
├── group-chat-assistant/        # Track 1 Cubbie Skill (personal Cubbie side); folder name = SKILL.md name
│   ├── SKILL.md  cubbie.yaml
│   ├── reference/group-link.md
│   └── scripts/groupsync.py     # client for the API in phase 5
├── bot/
│   ├── client.py                # bot setup, sync, error handler, persistent views
│   ├── commands.py              # /help /setup /quiz … /link /unlink /me /group …
│   ├── views.py                 # buttons, selects, modals
│   ├── embeds.py                # brand style + text progress bars
│   ├── chatmode.py              # chat-mode transport for the engine
│   ├── popquiz.py               # text pop quizzes + scheduler
│   └── recap.py
├── game/
│   ├── state.py                 # dataclasses, registries, JSON snapshot
│   ├── engine.py                # shared rules: rounds, timers, damage, crit, counterattack
│   ├── ws.py                    # arena transport
│   └── api.py                   # Cubbie link API + inbox
├── llm/  client.py  prompts.py
├── ingest/extract.py
├── export/  kahoot.py  quizlet.py
├── static/  host.html  play.html  style.css  common.js  fx.js   # fx.js = GSAP/confetti/WebAudio helpers
├── scripts/  fake_players.py  fake_link.py
└── data/  sample_notes.md  sample_questions.json  sample_profiles.json
```

## 7. Data model (`game/state.py`)

```python
@dataclass
class Question:
    id: str; topic: str; prompt: str
    choices: list[str]            # exactly 4
    answer_index: int; explanation: str
    source: str = ""              # "Lecture 9, slide 12" from the course pack

@dataclass
class MemberProfile:              # exactly what groupsync.py may send
    display_name: str
    course: str = ""
    exam_dates: list[str] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)
    free_slots: list[str] = field(default_factory=list)
    notes_excerpt: str = ""

@dataclass
class Member:
    discord_user_id: int
    token: str                    # secrets.token_urlsafe(24)
    profile: MemberProfile
    results: list[dict] = field(default_factory=list)
    inbox: list[dict] = field(default_factory=list)

@dataclass
class Group:                      # one per channel
    channel_id: int; name: str
    course: str = ""; exam_date: str = ""; timer: int = 20
    members: dict[int, Member] = field(default_factory=dict)
    deck: list[Question] = field(default_factory=list)
    course_pack: dict = field(default_factory=dict)   # merged from members' Cubbies
    pop_schedule: dict | None = None                  # {every_h, quiet_from, quiet_to}
    last_weak_topics: list[str] = field(default_factory=list)

@dataclass
class Player:
    id: str; name: str
    discord_user_id: int | None = None
    score: int = 0; streak: int = 0; show_name: bool = True
    answers: dict[str, int] = field(default_factory=dict)

@dataclass
class Party:
    code: str; channel_id: int; host_user_id: int
    mode: str                     # "chat" | "arena"
    questions: list[Question]; players: dict[str, Player]
    state: str = "lobby"          # lobby | question | reveal | ended
    current_index: int = -1
    boss_hp: int = 100; boss_max_hp: int = 100
    boss_weakness: str = ""
    question_deadline: float | None = None
```

Globals: `GROUPS`, `PARTIES`, `LINK_CODES {code: (channel_id, user_id, expires_at, used)}` and `TOKENS {token: (channel_id, user_id)}`.

## 8. Environment (`.env` + `.env.example`)

```
DISCORD_TOKEN=
DISCORD_GUILD_ID=          # instant command sync in the dev server
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-5-5
PUBLIC_BASE_URL=http://localhost:8000
MOCK_LLM=false
```

## 9. LLM prompt rules (`llm/prompts.py`)

- JSON only, with the exact schema in the prompt. Strip ``` fences before calling `json.loads`.
- 4 plausible choices, exactly one correct, no "all of the above", a 4/4/2 easy/medium/hard mix, grounded in the notes.
- Pass in **aggregated** weak topics and the soonest exam, never individual profiles. Reuse members' `weak_topics` strings as tags when they match.
- Explainers are friendly, use one analogy, and stay at or under 80 words.
- Each call has a 30s timeout. On error, log it and fall back to sample data. **Never crash a game.**

## 10. Demo script (under 3 minutes)

1. Discord "CSE 230 study group". Someone runs `/link` and texts the code to their **real Cubbie** (iPhone on the projector). Cubbie lists what it will share. They reply "yes", and "🔗 linked · 3/4" appears. The others were pre-linked with `fake_link.py`.
2. `/quiz new` with `sample_notes.md`: the progress embed, then "Focused on caches, which 3 of you marked as weak · midterm in 5 days".
3. **📱 Play (Arena):** judges scan the QR and play. `?demo=1` gives 6 questions on 12s timers. Crits land on the weakness, and the boss counterattacks on the hard one.
4. The recap posts, then **📅 Schedule** shows the overlap poll ("Thu 7 pm fits 4/4").
5. Back on the iPhone, text "any group updates?". Cubbie offers to add Thursday's session to the calendar with a reminder. Then "how did I do?" gets a private breakdown and a 2-minute drill.
6. One sentence to close: "The group bot only sees aggregates; your Cubbie shares only what you approve, and brings the personal stuff back to you."

## 11. Working rules for Claude Code

- **Never run `git commit` or `git push`, and never add co-author lines.** At each ✅, stop and give the user a GitHub Desktop summary and description to commit.
- Build phase by phase and verify each one by running it.
- **Academic integrity:** quizzes cover concepts from course materials. Never generate questions from, or answers to, open graded assignments, even though Cubbie can read them.
- Never cut phases 3, 4 or 5. If behind, cut phase 8 first, then the phase 6 polish (keep a basic arena), then the phase 7 poll.
- No auth beyond member tokens. No DB, Docker, TypeScript, or frontend framework or build step.
- When something is ambiguous, pick the simpler option, leave a `# DECISION:` comment, and continue.
