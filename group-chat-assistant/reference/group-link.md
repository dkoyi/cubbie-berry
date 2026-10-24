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

## Share the course pack (the group's Canvas context)

Group Cubbie has no access to Canvas. You do. The course pack lets the group's quizzes follow what *this* class actually teaches. Only one linked member needs to share it. Others can add units later.

Right after a successful join, offer once:

> Want the group's quizzes to match your actual CSE 240 class? I'd share the unit outline, upcoming exam dates and short excerpts from lecture materials. No grades, no submissions, no assignment answers.

If they say yes:

1. **Read their Canvas** for that course: modules and pages, lecture files, the syllabus, and upcoming quizzes and exams with dates.
2. **Write `pack.json`:**

   ```json
   {"course": "CSE 240", "term": "Fall 2026",
    "units": [{"title": "Unit 4: Memory", "topics": ["caches", "TLB"], "summary": "≤600 chars", "source": "Lecture 9 slides"}],
    "upcoming": [{"title": "Midterm 2", "type": "exam", "due": "2026-10-30", "covers": ["caches", "TLB"]}],
    "excerpts": [{"topic": "caches", "text": "≤2000 chars, quoted from the material", "source": "Lecture 9, slide 12"}]}
   ```

   Limits: at most 12 units, 10 upcoming items, and 10 excerpts (about 20k characters in total). Use the exact topic names the course uses.
3. **Never include** grades, submissions, rubrics, the text of open graded assignments, or answers to them. Write `covers` as topic names only.
4. **Preview it in one message** ("8 units, 2 upcoming exams, 6 excerpts from lectures 7–12"), and run it only after they say yes: `python3 scripts/groupsync.py course --pack pack.json`.

## Put the group's deck on Kahoot or Quizlet

The group's deck lives on Group Cubbie. Run `python3 scripts/groupsync.py deck` to get it, then use whichever option the student wants.

- **Kahoot:**
  1. Create an Excel file in Kahoot's spreadsheet-import format: question ≤120 characters, 4 answers of ≤75 characters each, a time limit, and the number of the correct answer.
  2. Open kahoot.com in your browser. The student signs in by taking over the browser.
  3. Go to Create → Import spreadsheet, upload the file, and name the kahoot "<course> <topics>".
  4. **Ask before saving or publishing.** Then send the student the link to host it.
- **Quizlet:**
  1. Create the paste-ready import text: one `question<TAB>answer` line per card.
  2. Open quizlet.com in your browser. The student signs in by taking over the browser.
  3. Create a set → Import, paste the text, and title it.
  4. **Ask before saving.** Then send the link.

If the site's layout changed or the import fails, send the student the file or the text along with the 3 steps to import it themselves.

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

## Updates from the group (Group Cubbie → you)

Group Cubbie can't message you directly. It leaves messages in the student's inbox on its server, and you pick them up.

**Set up the check-in.** Right after a successful join, offer once:

> Want me to check <group> for updates every evening? I'd suggest 6 pm. I'll only text you if there's something new.

If they say yes, create a daily scheduled check-in at the time they pick. The check-in runs `python3 scripts/groupsync.py inbox`. If it prints `NO_UPDATES`, send the student nothing.

**On demand.** Also run the inbox when the student asks "any group updates?" or "what's my group doing?".

Each message has a `kind`. Handle each one in 1–2 short messages:

- **`session`** (`{when, where, course}`): "Study session Thu 7 pm, <where>. Add it to your calendar and remind you at 6?" Add it to Google Calendar and set the reminder only after they say yes. If it's an early exam-day session, offer a wake-up call too.
- **`results`**: tell them a group game finished and they can say "how did I do?". Or, if they asked for results automatically, run `results` and follow "After a group game".
- **`nudge`** (`{question, choices, answer_index, explanation, topic}`): send the question as a one-question quiz. Then reply ✅ or ❌ with the explanation, and update their remembered weak topics.
- **`deck`** (`{topics, exam}`): "Your group's new quiz covers <topics>. Want a 3-question warm-up first?"
- **`pack_request`** (`{course, unit, reason}`): the group wants material you haven't shared. Ask: "Your group is quizzing on <unit>. Share that unit from Canvas?" Only if they say yes, add that unit to the pack and share it as described in "Share the course pack".
- **Any other kind:** summarize the `text` field in one line.

## Leave

If they say "leave the group", "unlink", or "stop sharing", run `python3 scripts/groupsync.py leave`. Confirm that the group server deleted their profile, and forget the link. `python3 scripts/groupsync.py list` shows the groups they're linked to.
