# Design audit and plan for the main study

Audit date: 4 November 2026, the night before the first pilot sessions.
Scope: the progress report (`practice_makes_calm_progress_report.pdf`), the app code, the consent form and the questionnaire draft.

Status words used here:
- **Changed** means the code now does it, and it is covered by a test.
- **Open** means a decision or a pilot result is still needed.
- **Paper** means the methodology text must be updated.

## 1. What already worked

- The session flow matches the paper, step by step.
- The adaptive rule is plain code. Every decision and its inputs are logged.
- The judge (LLM 2, live, adaptive design only) and the scorer (LLM 3, offline, blind) are separate.
- The scorer gets shuffled transcripts with conditions removed, and scores three times.
- Double clicks and resent forms cannot skip a step.
- Pilot participants are kept out of the main analysis.
- The tests cover the controller, the counterbalancing, STAI scoring and a full session.

## 2. Weaknesses found, and what was done

### 2.1 Dr. Lee felt "too easy" or "pushing on purpose" (Changed, Paper)

This is what the team saw in the first prototype test. There were two causes in the prompt.

1. **Level 1 agreed on "any reason".** The cooperative Dr. Lee usually agreed after the first message. The round was over before any practice happened.
2. **Levels 2 and 3 were written as quotas.** The prompt said "push back up to three times". Language models tend to use up a quota. So Dr. Lee kept pushing even after the student had already given the reason, the plan and the date. That is what felt scripted.

What changed:
- There is a new shared block of conversation rules for all levels (`prompts.CONVERSATION_RULES`):
  - React to what the student just said.
  - Acknowledge a fair point.
  - Never ask again for something already given.
  - Treat push-back numbers as maximums.
  - Agree as soon as the criteria are met.
- **L1** now agrees once the student gives a reason and says what they want. If one is missing, it asks one friendly question.
- **L3** pushes back at least once, then agrees when its criteria are met. It picks the move that fits the weakest part of the student's case.

The three levels still differ in tone, in the moves allowed and in what is needed to agree. This keeps the manipulation, but each level should now feel less mechanical.

Paper: Table 2 and Appendix A must describe the new rules. "Agrees when: any reason" becomes "reason + request" for L1.

### 2.2 Practice with the firm partner rehearsed the probe (Changed, Paper)

The L3 style examples used nearly the same words as the fixed probe lines.
- S1: "A whole week is a lot..."
- S2: "Reviewers ... expect accuracy"
- S3: "only a few hours"

So practice with the fixed-resistant design rehearsed the test itself. That alone could produce H1a (F > C on probe DESC).

What changed: all style examples were rewritten so they share no wording with the probe. A test now checks this.

The move types still overlap, because doubt, social pressure and asking for specifics are what resistance is. Paper: name this overlap as a limitation.

### 2.3 The four repeated attempts per partner felt boring (Changed, Open)

Each block has two practice rounds of the same scenario, then the probe. That means the same request three times in a row.

What changed:
- Round 2 now shows "Fresh start: Dr. Lee does not remember the last round. You can try a different approach."
- An optional one-line reflection sits between rounds ("Is there one thing you want to try differently?").
- The reflection is the same for every design, so it does not bias the comparison. It also gives qualitative data for RQ2.
- It can be switched off with `REFLECTION_PROMPT=0`.

Open: if pilots still find it long, lower `ROUND_MAX_MESSAGES` from 5 to 4. That is the fallback already written in the paper's Table 7.

### 2.4 Practice time is not equal across designs (Changed for reporting, Paper)

A cooperative Dr. Lee agrees sooner, so learners get fewer practice turns than with the fixed-resistant one. A DESC difference may partly reflect the amount of practice.

What changed: `blocks.csv` now reports, per block:
- `practice_learner_messages`
- `practice_seconds`
- `practice_rounds_agreed`
- `practice_rounds_skipped`
- `adaptive_levels`

Paper: report these next to probe DESC, and treat them as a possible explanation.

### 2.5 The adaptive design is mostly "medium difficulty" (Open, Paper)

Round 1 is always L2, and there is only one decision per block. So "A has lower anxiety than F" could only mean that L2 is easier than L3. It would not show that adapting helps.

Do this:
- Report how often the level actually changed (`adaptive_levels` in `blocks.csv`).
- Keep the claim modest in the paper.

A stronger option is three practice rounds (`PRACTICE_ROUNDS=3`). It gives two decisions per block, but adds about six minutes per session. Decide after the pilots, from the session length.

### 2.6 The judge and the scorer used different units (Changed, Paper)

- The live judge scores a whole round, using the best evidence for each DESC part.
- The offline scorer scored each probe reply on its own, and the paper averaged them.

One reply rarely covers all four parts, so per-reply means are squeezed toward the low end.

What changed:
- `score_transcripts` now also writes `scores_by_transcript.csv`. Its `desc_best` column is the best score per part across the probe, the same unit as the judge.
- The judge now sees the whole round with Dr. Lee's lines as context. It still scores only the student.

Paper: pick one primary unit before the main study. `desc_best` is recommended, with the per-reply mean as secondary.

### 2.7 No feedback at all (Changed)

Louie et al. (CHI 2026), cited as [19], found that practice without feedback can even lower skill.

What changed: the final page now shows a short DESC guide with examples, and the participant's own probe replies to look back on. It appears only after every measure is collected, so it cannot affect the data. It also makes the session worth the participant's time.

### 2.8 The visible countdown adds stress (Changed)

The timer turned orange in the last 30 seconds. That adds time pressure, and it can leak into the stress tap that the controller relies on.

What changed: the timer is now a quiet grey "Time left" label. The four-minute limit itself is unchanged.

### 2.9 "You may skip anything" was not true in the app (Changed)

Every form field was required, and there was no way to stop a round.

What changed:
- Chat rounds have an "I want to stop this round" link. It needs two clicks, so it cannot happen by accident, and it is logged as `skipped`.
- The monitor has a "Skip current step" button for the researcher. It is also logged.

### 2.10 Tagging without context (Changed)

The tag screen showed only Dr. Lee's lines.

What changed: it now shows the whole conversation. The participant's own turns appear in grey, and only Dr. Lee's turns can be tagged.

### 2.11 Data from two laptops could not be merged (Changed)

Each laptop picked "the next free sequence" from the same fixed order. Two laptops would hand out the same participant ID and the same sequence. The balanced square would break, and the databases could not be combined.

What changed:
- `STATION` and `STATION_SEQUENCES` in `.env`. Each laptop owns its own main sequences. Pilot IDs carry the station letter, for example `PILOTA03`.
- The console has a dropdown to choose a sequence by hand, for example when replacing a withdrawn participant.
- Every participant stores a **config hash**. It is a fingerprint of the prompts, materials, model and thresholds. Line endings are normalised, so Windows and Linux copies give the same hash.
- `export_bundle` writes one JSON file per laptop.
- `merge_bundles` loads all bundles into one fresh analysis database. It refuses:
  - duplicate IDs;
  - duplicate sequences;
  - mixed config hashes among main participants.

See the README, section "Two laptops".

### 2.12 Role-play blinding (Open, procedure)

The researcher who plays Dr. Lee in the human role-play must not watch the live monitor. The conversation shows how hard Dr. Lee pushed, and that reveals the design. Hidden labels on the monitor are not enough.

With everything on one laptop, this works if:
- one team member runs the session and the monitor;
- another team member, who stayed outside, plays Dr. Lee.

### 2.13 Instruments (Changed in docs, Paper)

The paper form `self-efficacy, difficulty, and realism questionnaire.md` did not match the app or the paper:
- It used general self-efficacy items. These are trait-like, so they barely change between blocks.
- It had no real difficulty item. Its "difficulty" items 4 to 6 were also self-efficacy items, and difficulty is the manipulation check.
- Item 9 appeared twice.
- Some answer labels did not fit their questions.

Decision: use the app's items, which are the ones the paper describes. Task-specific self-efficacy items follow Bandura's guide, and single difficulty and realism items keep three blocks short. See `docs/materials/Questionnaires.md`. The old form is superseded.

### 2.14 Consent form (Changed in docs)

The paper form did not say:
- that chat text is sent to the Anthropic API;
- how long data is kept;
- what happens if a person declines audio recording.

See `docs/materials/Consent_form_v2.md`. Add the retention period and contact details before use. Keep signed forms, which carry names, apart from the participant IDs.

### 2.15 Update after the first real-model check (4 Nov, morning)

The short P1 run (S1, 9 conversations) showed push-backs that rise with the level for every student type:

| Student type | L1 | L2 | L3 |
|---|---|---|---|
| weak | 1 | 2 | 3 |
| medium | 0 | 1 | 2 |
| strong | 0 | 0 | 1 |

There were no rule breaks, and the median latency was 1.8 s. The old Table 7 targets (L2 = 2, L3 = 3) assumed a fixed quota. Now push-backs depend on how complete the student's case is, so the pass rule is the order of the levels for the same student: L1 <= L2 <= L3, L1 at most 1, and L3 at least 1. `pilot_system` now prints this check.

Note: for a strong student, L1 and L2 behave the same (0 push-backs). That is realistic, but it means the cooperative and adaptive partners only differ for students who leave something out. Report this in the paper.

Two problems found in the transcripts, and in the team's own test, are now fixed:
1. **Dr. Lee quizzed students on facts that are not on the card.** Example: "Corrupted how? Was there no backup?" The simulated student had to invent a cause. This is also why a complete answer still drew questions. The model also copied the L3 style example word for word.
   Fix:
   - A new rule: accept the student's facts as true, do not ask about details that are not part of the situation, and push back on the request itself (timing, fairness, plan, cost).
   - When the student already gave everything, L3 uses its one push-back on fairness or the schedule.
   - The copied example was replaced, and there is a "never copy the examples" rule.
2. **The task felt like a reading and writing exam.** The card was a paragraph that people had to mine for facts.
   Fix:
   - The card is now a short bullet list with the key words in bold.
   - A line says "You do not need to use every fact, or the exact words."
   - The list stays on screen during the chat.
   - The same layout is used for the warm-up and for the human role-play card.

Self-efficacy items: the same wording is now used at baseline and after each block ("a difficult request", not "this kind of request", which made no sense before any scenario was shown). There is also a fourth item on persistence ("keep asking for what I need, even if my advisor disagreed at first"). Persistence is the skill a resistant partner trains, so it should be measured.

Human role-play: the researcher reads a fixed introduction (shown on the monitor). The researcher always says all three lines, even after a perfect first answer, adding "I see." before a line that was already answered.

### 2.16 Pilot P4 results (4 Nov, two pilot participants, sequences 2 and 3)

Both pilots had the design order C, F, A, so order and design cannot be separated in these two. That is fine for a pilot.

| | PILOT03 | PILOT02 |
|---|---|---|
| Session length | 41 min | 28 min |
| Difficulty C / F / A | 4 / 6 / 5 | 2 / 3 / 4 |
| Scenario in each block | C-S3, F-S1, A-S2 | C-S2, F-S3, A-S1 |

What the data shows:
- **S2 (F1-score versus accuracy) failed.** Both participants said it needed AI knowledge they did not have, and it stressed them.
  - PILOT03 hit the message limit in both S2 rounds. The judge scored DESC 3, then 1.
  - PILOT02 needed 4 and 3 messages even with the cooperative partner, which normally agrees after one or two. The stress tap was 6, and the block STAI was 63, the highest of that session.
  - So S2 measured domain knowledge, not assertiveness. **Changed:** S2 is now "Disagreeing about thesis scope" (keep one research question, list the second as future work). It is the same task type, disagreeing with the advisor's feedback, and every argument it needs is on the card. The probe lines keep the same three moves: doubt, social pressure, ask for a plan.
- **The manipulation check passed.** Difficulty was C < F for both participants.
- **The cooperative partner gave almost no practice.** PILOT03 sent one message per round in C-S3 (20 to 36 s) and tagged it "too easy" twice. Expected, but it confirms the practice-exposure issue in 2.4.
- **The adaptive partner never raised the level.** Raising needs DESC 6 or more. The best judge score was 5, even for a round that ended in agreement. Open: consider lowering the raise threshold to DESC 5 (P3).
- **The controller ran after the last practice round**, where its decision is never used (PILOT03: "lower" after round 2). **Changed:** after the last round the judge score is still saved, but the decision is logged as `none(last_round)`.
- **No one used the reflection box.** Open: drop it, or keep it as optional.
- **Sessions took 28 to 41 minutes, well under the 60 planned.** There is time for `PRACTICE_ROUNDS=3`, which would give the adaptive partner two decisions per block instead of one (see 2.5).
- **Stress stayed low** (taps of 0 to 6). No pause was triggered.

Paper: replace S2 in Table 4 and Appendix C. Pilot data from before this change used the old S2, and its config hash differs.

Decisions taken after the pilots (team, 4 Nov):
- `PRACTICE_ROUNDS=3` (two adaptive decisions per block). The planned session length grows by about 6 to 8 minutes. The pilots suggest about 35 to 50 minutes.
- `RAISE_IF_DESC_GE=5` (was 6).
- `REFLECTION_PROMPT=0` (off).
- Tags stay as they are: unrealistic, too harsh, too easy, helpful. A pilot participant asked for a "neutral" tag. We did not add one, because a tag is meant to mark a turn that stood out, and "untagged" already means neutral. A neutral tag would add a click to every turn, and it does not answer RQ3. The tag screen now says so: "If a message felt normal or okay, leave it untagged." Known limitation: untagged cannot tell "neutral" from "not looked at". The interview question "When did Dr. Lee stop feeling real?" covers that gap.

## 3. Things that are not problems

- With n = 5, the descriptive analysis plan is right. Do not add significance tests.
- The fixed human script that says all three lines every time is a fair choice for standardisation. Expect some "unrealistic" remarks about it in the debrief, and record them.

## 4. Plan from now to the main study

| When | What | Pass rule (paper, Table 7) |
|---|---|---|
| Before pilot day | P1 short system run on the real model (`pilot_system --scenarios S1`), and read the transcripts | L1 <= L2 <= L3 for each student type; zero rule breaks; latency at most 4 s |
| Pilot day | 2 participant pilots (P4), with the checklist in `PILOT_DAY_CHECKLIST.md` | Session at most 70 min; difficulty C < F; instructions understood |
| After pilots | Full P1 (all scenarios), P2 judge calibration on about 40 replies, P3 with real stress and DESC values | ICC at least .75; judge within 1 point on 80% of replies |
| After pilots | Decide `PRACTICE_ROUNDS` (2 or 3), `ROUND_MAX_MESSAGES` (5 or 4), and whether to keep the reflection | Based on session length and pilot comments |
| Freeze | Freeze `content.py`, `prompts.py`, `.env`. Write the config hash into the paper. Both laptops must show the same hash | Same hash on both consoles |
| Main study | Laptop A: `STATION=A`, `STATION_SEQUENCES=1,8,15`. Laptop B: `STATION=B`, `STATION_SEQUENCES=6,10` | No duplicate IDs |
| Analysis | `export_bundle` on each laptop, `merge_bundles` into `analysis.sqlite3`, then `export_csv` and `score_transcripts` | Merge reports one config hash |

## 5. Paper edits needed

1. Table 2 and Appendix A: the new level rules and conversation rules; the new style examples. Table 7: the P1 pass rule is now the order of levels per student type. Appendix C: cards as fact lists. Self-efficacy: four items.
2. Section 3.1: the judge sees the whole round; the timer is quiet; there is a stop-round option and an optional reflection between rounds.
3. Section 3.5: the DESC feedback page at the end of the session.
4. Section 3.6: the primary probe DESC unit (`desc_best`); report practice exposure.
5. Section 4: the move-type overlap between L3 and the probe; adaptive is weak with one decision; the possible confound from unequal practice time.
6. Section 3.3: two laptops, station split, config hash.
7. Pilot data note: pilot sessions before this audit used the old prompts. Their config hash differs, so they must not be pooled.
