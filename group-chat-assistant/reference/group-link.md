# Linking to a Group Cubbie

Group Cubbie is a bot that lives in the study group's Discord server. Everyone in the group uses it together. This student's personal Cubbie never joins the group. It hands Group Cubbie a small, approved profile so the group games are built around what everyone needs. The group never sees the student's raw data.

All commands run from the skill folder. The script prints a short result, or a line starting with `ERROR:`.

## Join

The student types `/link` in the group's Discord channel. Group Cubbie privately shows them a message like this:

> Text your Cubbie: link my study group ABCD-1234 https://xyz.trycloudflare.com

When the student sends that to you:

1. **Gather** the data for the group's course:
   - the student's Canvas exam and quiz dates for that course,
   - their remembered weak topics for that course,
   - their free evening slots this week, from Google Calendar, as coarse blocks such as "Tue 7-10pm". Never include event titles.
2. **Show exactly what would be shared** and ask:

   > Share with <group> on Group Cubbie?
   > • Name: Dhanush
   > • Course: CSE 240
   > • Exams: Midterm 2 (Oct 30)
   > • Weak topics: pointers, recursion
   > • Free: Tue 7-10pm, Thu 8-11pm
   > Reply yes, or tell me what to leave out.

   Default to their first name. If they ask for a nickname, use that.
3. **Write only the approved fields** to `profile.json` in the working directory. The allowed keys are `display_name`, `course`, `exam_dates`, `weak_topics`, `free_slots` and `notes_excerpt`. Leave out any key they declined. Only include `notes_excerpt`, up to about 12k characters of their notes for the unit, if they offered to share notes.
4. **Run:** `python3 scripts/groupsync.py join --code ABCD-1234 --server https://xyz.trycloudflare.com --profile profile.json`
5. **Reply:** "You're linked to <group>. Group Cubbie will build the next game around the group's weak spots." Remember that the student is linked to that group, for that course.

Error handling:

- **Expired code:** ask them to type `/link` again for a new code.
- **Server unreachable:** "Group Cubbie looks offline right now. Try again later." Don't retry more than once.
- **Server address rejected** (not on the allowed hosts): tell them the link looks wrong and ask them to copy it again from Discord.

## Keep the group current (ask first)

After a solo quiz where the weak topics changed, or when a new exam date shows up, offer:

> Update <group> with your new weak spots?

If they say yes, rebuild `profile.json` with the same approved fields and run `python3 scripts/groupsync.py update --profile profile.json`.

## After a group game: private results

When the student asks how they did, or says the game is over, run `python3 scripts/groupsync.py results`. It returns only this student's own per-topic results. The group recap shows only totals for the whole group.

Then:

1. Tell them their score and their weakest topic, privately, in 1–2 messages.
2. Update their remembered weak topics.
3. Offer a 2-minute solo drill on that topic now. If an exam is coming, offer the nightly drill too.

## Leave

If they say "leave the group", "unlink", or "stop sharing", run `python3 scripts/groupsync.py leave`. Confirm that the group server deleted their profile, and forget the link. `python3 scripts/groupsync.py list` shows the groups they're linked to.
