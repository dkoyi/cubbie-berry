# cubbie-berry: Group Cubbie

Team wildberry, DevHacks 2026.

The project uses two agents for one study group:

- **Group Cubbie** is one bot in the class group chat (Discord), and everyone uses it together. It runs Kahoot-style boss-battle quiz games on everyone's phones and posts a recap of the topics the *group* is weak on. *(Track 3, in progress; see [CLAUDE.md](CLAUDE.md).)*
- **Personal Cubbie** is each student's own Cubbie in iMessage, running our skill. It links to the group and shares only the info the student approves: name, course, exam dates, weak topics and free evenings. That lets every game target what the whole group needs. Afterwards, it brings each student's private results back to them. *(Track 1.)*

## Track 1 Cubbie Skill: `group-chat-assistant`

The skill lives in [`group-chat-assistant/`](group-chat-assistant/). It does three things:

- links the student to their study group's Group Cubbie (see [reference/group-link.md](group-chat-assistant/reference/group-link.md)),
- runs a solo quiz from the student's own Canvas material, notes, PDF or photo,
- runs a relay quiz for any group chat: the student pastes the questions into the group, then sends Cubbie a screenshot of everyone's answers to score.

**Install:** text Cubbie the link to the folder:

```
https://github.com/dkoyi/cubbie-berry/tree/main/group-chat-assistant
```

**Abilities used:** Canvas, files and media, memory, scheduled check-ins, Google Calendar, documents, and the code sandbox (`scripts/groupsync.py`, standard library only).

**Sign-in:** Canvas is already connected to Cubbie, so the student does nothing extra. `cubbie.yaml` declares only the Group Cubbie server hosts (`*.trycloudflare.com`, `*.onrender.com`). There are no keys or packages.

**Try:** "quiz me on CSE 240", "quiz my study group", or, once Group Cubbie is live, the `/link` code from Discord.

## What the agents share and when they ask

- The personal Cubbie shows the exact fields before sharing anything, and shares only after the student says yes. The script also drops any field outside a fixed allowlist.
- Group Cubbie posts only group-level totals. Each student's results go back only to their own Cubbie.
- "Unlink" deletes the student's profile from the group server.
- Scheduling, calendar events and nightly drills always need the student's yes.
