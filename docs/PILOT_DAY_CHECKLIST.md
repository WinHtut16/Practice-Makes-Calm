# Pilot day checklist (P4, two pilot participants)

This is the first run with the real model. Pilot data is never used in the main analysis.
The goal is to find problems, not to test hypotheses.

## Tonight or before the first pilot (PowerShell, in `drlee_app`)

```powershell
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate                       # adds the new fields (station, config hash, reflection)
$env:LLM_MOCK="1"; python manage.py test study; Remove-Item Env:LLM_MOCK   # expect "OK" (19 tests)
python manage.py list_models                   # confirm LLM_MODEL in .env is a model your key can use
```

Check `.env`:
- `LLM_MOCK=0` and a valid `ANTHROPIC_API_KEY`. The console shows a yellow warning in mock mode.
- `STATION=A` on this laptop. Leave `STATION_SEQUENCES` empty if only this laptop runs pilots. If the other laptop also runs pilots, set `STATION=B` there and `STATION_SEQUENCES=6,10`, and set `STATION_SEQUENCES=1,8,15` here.
- Set a spending limit in the Claude Console.

Short system pilot (P1) on the real model. It runs about 90 calls and costs well under a dollar with Sonnet.

```powershell
python manage.py pilot_system --scenarios S1 --runs 1
```

Then open `pilot_out\p1_..._transcripts.txt` and read it. Look for these things:
- The summary line says PASS (push-backs rise L1 <= L2 <= L3 for each student type).
- Dr. Lee does not ask about details that are not on the card (causes, backups, numbers).
- L1 agrees after a reason and a request, not on the very first word.
- L3 pushes back at least once, and does not keep pushing after the student gave a reason, a plan and a date.
- Dr. Lee never asks again for something the student already said.
- There are no grammar comments, no sarcasm and no lists.
- Median latency is at most 4 s.

If L3 still feels scripted, tell the team before the pilots. Do not edit prompts between the two pilots. Both pilots should see the same version.

## Room set-up (one laptop)

- The participant uses the laptop in full screen (F11).
- The researcher needs the monitor page, but the participant should not see it. Two options:
  1. **Phone or tablet on the same Wi-Fi (best).** Start the server with `python manage.py runserver 0.0.0.0:8000`. Find the laptop's IP with `ipconfig`, add it to `DJANGO_ALLOWED_HOSTS` in `.env` (for example `localhost,127.0.0.1,192.168.1.23`), and open `http://192.168.1.23:8000/researcher/` on the phone. Allow Python through the Windows firewall when asked. Wi-Fi with "client isolation", like some campus networks, blocks this. Use a phone hotspot then.
  2. **No second device.** Sit beside the participant. Check the monitor only during breaks.
- Whoever plays Dr. Lee in the human role-play should not watch the monitor. The live chat reveals the design.
- Have a voice recorder ready, the S4 script printed, and the consent form v2 printed.

## The human role-play (what to say)

1. When the app shows the role-play page, start the recorder and read the introduction on the monitor page, word for word.
2. Let the participant speak first. If they are silent for 5 seconds, say: "Yes? What did you want to talk about?"
3. After their first turn, say Line 1. After their next turn, say Line 2. After the next, say Line 3. Always all three, in order, with the exact words.
4. **If the student gave a perfect answer early, do not stop.** Say "I see." and then the next line as written. Every participant must answer all three lines, or their role-play scores cannot be compared. Hearing a point again is also part of the test: does the student hold their position or give in?
5. Between lines, use only "I see.", "Mm-hm.", "Go on." or "Can you say more?". For off-script questions: "Let's focus on the meeting for now."
6. End: if they gave a reason, a new time and a plan, say the agree line with their day. Otherwise say "I'd prefer to keep Thursday. Bring whatever you have."
7. Stop the recorder and press Continue on the laptop.

## During each session

Start: console, then **New pilot participant**. Open the participant link on the laptop.

Note the clock time at each of these points, so you can check Table 5:
- end of consent;
- end of pre-survey;
- the start and end of each block;
- the role-play;
- the end.

Watch for, and write down:
- Any moment the participant asks "what do I do now?" (instructions unclear).
- Long pauses before the first message of a round (scenario card unclear).
- Rounds that end by the time limit rather than by agreement. Note slow typing.
- Whether the reflection box is used or skipped.
- Whether the probe framing ("Dr. Lee is in a hurry") makes sense to them.
- Whether they understand the tag screen.
- Any stress tap of 8 or more. Note what happened just before it.
- Any error message or "Connection problem".

## Debrief after each pilot (5 to 10 minutes, think-aloud on screens)

Go back through the screens with them and ask:
1. Was any instruction or question unclear? Which one?
2. Did any Dr. Lee feel too easy, too pushy, or pushing on purpose? When?
3. Did the second practice round feel useful or repetitive?
4. Did the final check feel different from the practice? Did the "in a hurry" line explain it?
5. Was the session too long? Which part felt longest?
6. Did the face-to-face role-play feel like the AI conversations?
7. Was the stress question easy to answer honestly?

## After both pilots

```powershell
python manage.py export_csv --include-pilot
python manage.py export_bundle --include-pilot
```

Check in `exports\<time>\`:
- `participants.csv`: `minutes` (target at most 70).
- `blocks.csv`: `difficulty` (expect C < F), `practice_learner_messages`, `adaptive_levels`.
- `rounds.csv`: `end_reason`, `stress`, `judge_total`, `decision`.

Then decide, as a team:
- `ROUND_MAX_MESSAGES` (keep 5 or lower to 4);
- `PRACTICE_ROUNDS` (2 or 3);
- whether to keep `REFLECTION_PROMPT`;
- any wording changes.

After the last change, freeze the files and write the config hash shown on the console into the paper.
