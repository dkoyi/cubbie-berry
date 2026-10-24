# CLAUDE.md — Group Cubbie (DevHacks 2026 · Cubbie Track 3: Group Chat Assistant)

You are building a hackathon project with team **wildberry** (Malaika, Dhanush, Sashikant, Apoorv).
**Hard deadline: Sunday Oct 25, 2026, 12:00 PM (America/Phoenix).** Judging and demos run 2:00–4:30 PM.
Optimize for **a working, impressive live demo**, not for perfect architecture.

---

## 1. What we're building

**Group Cubbie** is a study-game bot for a class group chat (a Discord server). It works as one of **two kinds of agents**:

- **Group Cubbie** (this repo's server): **one** bot per group chat, which everyone uses together. It runs Kahoot / Netflix-party-style games. `/party` posts a QR code, everyone plays a **Boss Battle** on their phones, and a shared host screen shows the boss losing HP. Afterwards it posts a **group recap** showing which topics the *group* is weak on, with a short explainer for each.
- **Personal Cubbie** (each student's own Cubbie in iMessage, running our Track 1 skill in [group-chat-assistant/](group-chat-assistant/)): it knows the student privately (Canvas, memory, calendar). When a student links it, it sends Group Cubbie **only the fields that student approves**: display name, course, exam dates, weak topics, free evenings, and optionally a notes excerpt. After a game, it pulls back that student's **private** results.

**Why one group bot and not several Cubbies in the chat:** Cubbie can't join group chats. Several bots in one chat would also be noisy, race to answer each other, and leak private data. This is the standard bot pattern (Slack and Discord apps, like the GitHub or Spotify bots): **the students add themselves plus one bot, and each student links their own account** with a one-time code.

**The judge's "we need this" moment:** Group Cubbie *already knows* three of the four players are weak on recursion and that the midterm is Thursday. So the boss is "weak to recursion" and the game drills exactly that. The recap tells the group what it collectively missed. Each student's personal Cubbie then privately offers them a 2-minute drill. Track 3 asks teams to show **what agents share, how they handle conflicting constraints, and when they ask for confirmation**. Section 8 covers that.

---

## 2. Stack (do not change without asking)

- **Python 3.11+**
- **Discord bot:** `discord.py` 2.x with slash commands (app_commands)
- **Game server + link API:** `FastAPI` + native WebSockets (`uvicorn[standard]`)
- **Frontend:** plain HTML/CSS/vanilla JS, with two pages: `host.html` (big screen) and `play.html` (phone controller). No React and no build step.
- **LLM:** Anthropic Claude API via the `anthropic` SDK. Read the model from env `LLM_MODEL` (default `claude-sonnet-5-5`). Wrap every LLM call in one module.
- **PDF parsing:** `pypdf`
- **QR:** `qrcode[pil]`, saved as a PNG and attached to the Discord message
- **State:** in-memory dicts plus an optional JSON file dump. **No database.**
- **Public URL:** `cloudflared tunnel --url http://localhost:8000`, which gives `https://<random>.trycloudflare.com`, or deploy to Render (`*.onrender.com`). **The personal Cubbie skill can only reach `*.trycloudflare.com` and `*.onrender.com`** (as declared in `group-chat-assistant/cubbie.yaml`), so don't use ngrok. `PUBLIC_BASE_URL` drives both the QR link and the link-code message.

Run the bot and the server in **one process**: the bot is an asyncio task inside FastAPI's lifespan, so they share memory.

---

## 3. Environment variables (`.env`, and also provide `.env.example`)

```
DISCORD_TOKEN=
DISCORD_GUILD_ID=          # for instant slash-command sync during dev
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-5-5
PUBLIC_BASE_URL=http://localhost:8000
MOCK_LLM=false             # true = canned questions, no API calls
```

**MOCK_LLM must work.** The whole demo has to run end to end with no API key, using `data/sample_questions.json`.

---

## 4. File structure (repo root)

```
cubbie-berry/
├── CLAUDE.md
├── README.md
├── group-chat-assistant/   # Track 1 Cubbie Skill (personal Cubbie side). Its folder name must match SKILL.md `name`.
│   ├── SKILL.md
│   ├── cubbie.yaml
│   ├── reference/group-link.md
│   └── scripts/groupsync.py   # client for the link API in section 6, phase 2.5
├── requirements.txt
├── .env.example
├── main.py                 # FastAPI app + starts the Discord bot in lifespan
├── bot/
│   ├── __init__.py
│   ├── client.py           # slash commands: /ping /study /link /party /members
│   └── recap.py
├── game/
│   ├── __init__.py
│   ├── state.py            # dataclasses + registries
│   ├── engine.py           # rounds, timers, scoring, boss HP
│   ├── ws.py               # WebSocket routes
│   └── api.py              # link API for personal Cubbies
├── llm/
│   ├── __init__.py
│   ├── client.py           # call_llm(prompt, schema) -> dict; handles MOCK_LLM
│   └── prompts.py
├── ingest/
│   └── extract.py
├── static/
│   ├── host.html
│   ├── play.html
│   ├── style.css
│   └── common.js
├── scripts/
│   ├── fake_players.py     # N fake WebSocket players
│   └── fake_link.py        # links fake personal-Cubbie profiles for testing
└── data/
    ├── sample_notes.md
    ├── sample_questions.json
    └── sample_profiles.json  # 3 fake linked members for the demo
```

---

## 5. Data model (`game/state.py`)

```python
@dataclass
class Question:
    id: str
    topic: str            # short tag, e.g. "cache associativity"
    prompt: str
    choices: list[str]    # exactly 4
    answer_index: int
    explanation: str

@dataclass
class MemberProfile:      # exactly what groupsync.py may send, nothing else
    display_name: str
    course: str = ""
    exam_dates: list[str] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)
    free_slots: list[str] = field(default_factory=list)
    notes_excerpt: str = ""

@dataclass
class Member:
    discord_user_id: int
    token: str            # secrets.token_urlsafe(24); only the personal Cubbie holds it
    profile: MemberProfile
    results: list[dict] = field(default_factory=list)  # private per-game results

@dataclass
class Group:              # one per Discord channel
    channel_id: int
    name: str             # "#cse240-study"
    members: dict[int, Member] = field(default_factory=dict)  # by discord_user_id
    deck: list[Question] = field(default_factory=list)

@dataclass
class Player:
    id: str
    name: str
    discord_user_id: int | None = None   # set if they joined via their personal link
    score: int = 0
    answers: dict[str, int] = field(default_factory=dict)
    show_name: bool = True

@dataclass
class Party:
    code: str
    channel_id: int
    questions: list[Question]
    players: dict[str, Player]
    state: str            # "lobby" | "question" | "reveal" | "ended"
    current_index: int = -1
    boss_hp: int = 100
    boss_max_hp: int = 100
    boss_weakness: str = ""  # topic shown on the host screen
    question_deadline: float | None = None
```

Globals: `GROUPS: dict[int, Group]`, `PARTIES: dict[str, Party]`, `LINK_CODES: dict[str, tuple[channel_id, discord_user_id, expires_at]]`, and `TOKENS: dict[str, tuple[channel_id, discord_user_id]]`.

---

## 6. Features, in build order

### Phase 1: Skeleton (1 hour)
- `main.py` serves `/static`, `/host/{code}` and `/play/{code}`.
- The bot connects and syncs commands to `DISCORD_GUILD_ID`. `/ping` works.
- ✅ The bot is online, and `localhost:8000/host/TEST` loads.

### Phase 2: Ingest + question generation (1.5 hours)
- **`/study`** takes an optional attachment (PDF/.txt/.md) or a `text` arg. If neither is given, it uses the last 50 channel messages **plus the linked members' `notes_excerpt`s**.
- Generate **10 questions** as strict JSON covering 3–5 topics. Validate, retry once, then fall back to the sample deck.
- **Personalize using linked profiles**, with no individual data exposed:
  - About 50% of the questions target the most common `weak_topics` across members.
  - About 30% cover what's on the **soonest** exam.
  - About 20% are general review.
- The reply embed says: "📚 10 questions on caches, TLBs, pipelining. Focused on what 3 of you marked as weak. Midterm in 5 days. `/party` to battle."
- ✅ Test with `data/sample_notes.md`, with `MOCK_LLM=true`, and with `scripts/fake_link.py` profiles.

### Phase 2.5: Linking personal Cubbies (1 hour). This is the two-agent piece.
- **`/link`** creates a code like `ABCD-1234` that expires in 15 minutes and is tied to (channel, user). The bot replies **ephemerally**:
  `Text your Cubbie: link my study group ABCD-1234 {PUBLIC_BASE_URL}`
  plus one line on what will be asked and that the student approves every field.
- **API (`game/api.py`)** — this must match `group-chat-assistant/scripts/groupsync.py` exactly:
  - `POST /api/link` `{code, profile}` → `{group_id, group_name, member_token, members_linked}`. The code is single-use. `group_id` = str(channel_id).
  - `PUT /api/member` (Bearer token) `{profile}` → `{ok: true}`
  - `GET /api/member/results` (Bearer) → `{group, games: [{date, score, rank, per_topic: {topic: [right, total]}, weakest}]}`. **Only this member's results.**
  - `DELETE /api/member` (Bearer) → deletes the member's profile and results, and returns `{ok: true}`.
  - Errors return 4xx with `{"error": "..."}`. Expired or unknown codes return 410 or 404.
  - Server-side, validate the profile against `MemberProfile` and drop unknown keys.
- When a profile arrives, the bot posts in the channel: "🔗 Dhanush's Cubbie linked (CSE 240). 3/4 members linked." Name and course only. **Never post the shared fields.**
- **`/members`** shows who is linked and the group aggregate ("weak spots across the group: recursion ×3, pointers ×2; soonest exam: Oct 30"). Never show per-person weak topics.
- ✅ Run `scripts/fake_link.py` to link 3 sample profiles, then check that `/members` shows the aggregate and `/study` focuses on it.

### Phase 3: Party + live game (4 hours, the core)
- **`/party`** creates a `Party` and posts an embed containing the join code, a QR code linking to `{PUBLIC_BASE_URL}/play/{code}`, and a link to the host screen. It also sets `boss_weakness` to the group's top weak topic.
- WebSocket: `/ws/{code}?role=host|player&name=...`
- **Protocol** (JSON, with a `type` field):
  - `lobby` `{players}` · host `start` · `question` `{index, total, prompt, choices, topic, deadline_ms}` (never send `answer_index` before the reveal)
  - player `answer` `{choice}` (one per question) · `answered_count` `{n, total}`
  - `reveal` `{answer_index, explanation, per_choice_counts, damage, boss_hp, leaderboard}` · host `next` · `ended` `{leaderboard, boss_defeated}`
- **Game feel (Kahoot / Netflix-party):**
  - 20s per question, auto-revealed when everyone has answered.
  - Damage = `10 + speed_bonus(0–5)`. A correct answer on a `boss_weakness` question is a **critical hit** (×2 damage with a big flash).
  - Answer streaks show 🔥 on the phone.
  - Set `boss_max_hp ≈ total_q * players * 0.7 * 12`.
  - If fewer than 50% get a question right, the **boss counterattacks** with a screen shake.
  - The last question is "FINAL BLOW", worth double.
- **`host.html`:** big boss (CSS or emoji, no copyrighted art) with a weakness badge, an HP bar, the question with 4 colored boxes, a timer ring, a reveal bar chart, and the leaderboard. Dark theme, big type.
- **`play.html`:** mobile-first. Name entry, then a "show my name on the leaderboard" checkbox, then 4 giant buttons, then "locked in", then correct/wrong feedback with damage and streak. If the URL has `?u=<discord_user_id>`, tie the player to their member record so personal results can be saved.
- Reconnect handling: a reload with the same name restores the player's score.
- ✅ Three tabs or `scripts/fake_players.py` play a full game.

### Phase 4: Group recap (1.5 hours, the wow)
- Compute per-topic accuracy for the whole group. Topics below 60% are weak, worst first.
- The LLM writes an explainer (≤80 words) plus a practice question for the top 1–2 weak topics, using the notes as context.
- **Save each linked player's own per-topic results** into `Member.results`, which serves `GET /api/member/results`.
- The recap embed shows the 🏆 result and top 3 (opted-in names only), "📉 The group struggled with…", a 💡 explainer, and the buttons `▶ Rematch on weak topics` and `📅 Schedule next session`.
- Add the footer: "Your personal Cubbie has your private breakdown. Text it 'how did I do?'"
- ✅ The recap appears in Discord within 5 seconds of the game ending.

### Phase 5: Privacy, conflicts, confirmation (1 hour, Track 3 points)
- **What's shared:** personal Cubbie sends only fields the student approved, and the script whitelists them. Group Cubbie shows only aggregates. Individual results go back only to that student's own Cubbie, through their token.
- **Conflicting constraints** (show at least one in the demo):
  - *Different exam dates:* the deck weights the soonest exam, and the embed says so.
  - *Availability:* `📅 Schedule next session` intersects members' `free_slots` and offers the top 3 overlaps as a Discord poll. If there's no overlap, it offers the slot that fits the most people and names how many can make it, not who can't.
  - *Opt-outs:* a member who shared no weak topics still plays and is simply left out of targeting.
- **Ask before acting on the group:** before posting the recap, ephemerally ask the `/party` host "[Post] [Edit] [Skip]", and auto-post after 30s.
- Document all of this in the README under "What the agents share and when they ask".

### Phase 6: Stretch (only if Phases 1–5 are solid)
1. `/teachback`: ask a random player to explain the weakest topic, and have the LLM grade and fill gaps.
2. A daily 9 PM nudge in the channel with one question on the group's weak topics.
3. A speed-round game mode.

---

## 7. LLM prompt rules (`llm/prompts.py`)

- JSON only, with the exact schema in the prompt. Strip ``` fences before calling `json.loads`.
- 4 plausible choices, exactly one correct, no "all of the above". Mix difficulty 4 easy / 4 medium / 2 hard, grounded in the provided notes.
- Pass the group's aggregated weak topics and the soonest exam into the generation prompt, never individual profiles.
- Use short, consistent `topic` tags, and reuse the members' `weak_topics` strings when they match.
- Recap explainers are friendly and concrete, use one analogy, and stay under 80 words.
- Each call has a 30s timeout. On error, log it and fall back to sample data. **Never crash the game loop.**

---

## 8. Demo script (under 3 minutes)

1. Show the Discord channel "CSE 230 study group". Someone types `/link`, texts the code to their **real Cubbie** on iPhone (projected), and Cubbie shows the share-confirmation list. They reply "yes", and "🔗 linked, 3/4 members" pops up in Discord. The other members were pre-linked with `fake_link.py`.
2. Run `/study` with `sample_notes.md`. The embed reads: "Focused on caches, which 3 of you marked as weak. Midterm in 5 days."
3. Run `/party`. **Judges scan the QR and play.** `?demo=1` gives 6 questions on 12s timers. The boss is weak to "cache associativity", so critical hits land.
4. The boss counterattacks on a hard question.
5. The recap lands: "the group struggled with cache associativity", plus the explainer and a Rematch button. Then `📅 Schedule` resolves the free-slot overlap.
6. Back on the iPhone, text "how did I do?". The personal Cubbie privately replies with that student's weakest topic and offers a 2-minute drill. Wrap up in one sentence: "Group Cubbie shares only aggregates; personal Cubbies share only what you approve, and bring your private stats back to you."

---

## 9. Working rules for Claude Code

- **Never run `git commit` or `git push`, and never add co-author lines.** At each checkpoint, stop and tell the user what to commit in GitHub Desktop, with a suggested summary and description.
- Work phase by phase, and verify each phase by running it. `scripts/fake_players.py` and `scripts/fake_link.py` let you test without phones.
- Keep it simple: no auth beyond member tokens, and no DB, Docker, TypeScript, or frontend frameworks.
- Keep `game/api.py` in sync with `group-chat-assistant/scripts/groupsync.py`. If you change one, change both.
- If a decision is ambiguous, pick the simpler option, leave a `# DECISION:` comment, and continue.
- If behind schedule, cut Phase 6 first, then the Phase 5 schedule poll. Never cut Phases 2.5, 3 or 4.
- `play.html` must work on iPhone Safari: no hover UI, buttons at least 64px tall, and the viewport meta set.
- Write a README at the end covering Discord app setup (Message Content intent, `bot` + `applications.commands` scopes), `pip install -r requirements.txt`, `.env`, `python main.py`, the `cloudflared` command, and the demo flow.

## 10. Reminder for the team (not for code)

Track 3 only counts if the Track 1 Cubbie Skill (`group-chat-assistant/`) has been submitted within the first 10 hours.
