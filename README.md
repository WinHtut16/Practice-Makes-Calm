# Practice Makes Calm: Dr. Lee study app

The web app for the Ctrl+Human study. It runs the full participant session from the paper's Methodology section (consent, pre-survey, warm-up, 3 blocks of 2 practice rounds + probe + survey + tags, breaks, human role-play, ranking) and includes a researcher console and command-line tools for pilot testing, blind scoring and data export.

## 1. Set up (once)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then put your Claude API key in .env
python manage.py migrate
python manage.py createsuperuser  # researcher login
python manage.py list_models      # check which model IDs your key can use; set LLM_MODEL
```

No key yet? Set `LLM_MOCK=1` in `.env`. A fake Dr. Lee lets you click through everything without any API calls.

## 2. Run a session

```bash
python manage.py runserver
```

1. Open http://127.0.0.1:8000/researcher/ and log in.
2. Click **New participant** (or **New pilot participant** for pilots). Main participants get the 5 balanced sequences (P01, P06, P08 first, then P10, P15; paper, Table 3). Pilot participants get the other sequences, so pilots never use up a main slot.
3. Open the **participant link** on the participant's laptop (full screen).
4. Keep the **monitor** page open on your own laptop. It shows the current step, live conversation, stress alerts (9-10), and, during the human role-play, the S4 script. Conditions are hidden by default so the role-play researcher stays blind; click *Reveal* only if you are not playing Dr. Lee.
5. Type interview notes into the monitor page at the end.

## 3. How the app maps to the paper

| Paper | Where in the code |
|---|---|
| Dr. Lee persona, shared rules, level slot (Table 2, Appendix A) | `study/prompts.py`, `study/content.py` (`LEVEL_RULES`) |
| Scenarios, probe lines, S4 script (Table 4, Appendix C) | `study/content.py` (`SCENARIOS`, `S4`) |
| Adaptive rule | `study/controller.py` (deterministic code) |
| Judge (LLM 2) and scorer (LLM 3), DESC rubric (Appendix B) | `study/prompts.py` |
| Counterbalancing, random assignment | `study/counterbalance.py` |
| Session steps and timings | `study/flow.py`, `.env` |
| Questionnaires (STAI-6, self-efficacy, ratings) | `study/content.py` |

Edit wording in `content.py` and `prompts.py`, not in the HTML templates.

## 4. Pilot testing commands (paper, Section 3.7)

| Stage | Command |
|---|---|
| P1 System | `python manage.py pilot_system --runs 1` (simulated weak / medium / strong learners vs. every level and scenario; writes a CSV and transcripts to `pilot_out/`) |
| P2 Judge | `python manage.py calibrate_judge replies.csv` (CSV columns: `scenario,reply,human_a,human_b`; reports ICC and % within +/-1) |
| P3 Controller | `python manage.py pilot_controller` |
| P4 Session | run 3-4 **pilot participants** through the app, then `python manage.py export_csv --include-pilot` and check timings in `participants.csv` (`minutes`) and difficulty ratings in `blocks.csv` |

After P4, freeze `.env`, `content.py` and `prompts.py`. Pilot data is excluded from all exports unless you pass `--include-pilot`.

## 5. After the study

```bash
python manage.py export_csv                       # all data -> exports/<timestamp>/ (two laptops: merge first, section 6)
python manage.py score_transcripts --practice --roleplay-dir roleplay_txt/
python manage.py compare_human_scores             # after the human rater fills human_rating_sheet.csv
```

`score_transcripts` scores every probe reply (and role-play transcripts saved as `P07.txt` files with `Dr. Lee:` / `Student:` lines) three times with the scorer model and keeps the median. It writes `scores_blind.csv`, a separate key file, and a 25% sample sheet for the human rater. Give the rater **only** the sample sheet.

## 6. Two laptops: keeping IDs apart and merging the data

Each laptop keeps its own `db.sqlite3`. To make the two databases mergeable:

1. **Before the first session**, give each laptop its own station and its own main sequences in `.env`:

   | Laptop | `.env` |
   |---|---|
   | A | `STATION=A` and `STATION_SEQUENCES=1,8,15` |
   | B | `STATION=B` and `STATION_SEQUENCES=6,10` |

   Pilot IDs then carry the station letter (`PILOTA03`, `PILOTB04`), so pilots never clash either. The console shows the station and lets you pick a sequence by hand, for example to replace a withdrawn participant.
2. **Use the same code and settings on both laptops.** The console shows a *config hash*: a fingerprint of the prompts, materials, model and thresholds. Both laptops must show the same hash for the main study.
3. **After the sessions**, on each laptop:

   ```powershell
   python manage.py export_bundle                  # add --include-pilot for pilot data
   ```

   This writes `bundles\bundle_A_<time>.json`. Copy both files to one laptop. They contain chat text, so share them privately and never commit them.
4. **Merge into a separate analysis database** (the laptops' own data is not touched):

   ```powershell
   $env:DB_NAME = "analysis.sqlite3"
   python manage.py migrate
   python manage.py merge_bundles bundles\bundle_A_....json bundles\bundle_B_....json
   python manage.py export_csv
   python manage.py score_transcripts --practice --roleplay-dir roleplay_txt/
   Remove-Item Env:DB_NAME
   ```

   The merge refuses duplicate IDs or sequences, and refuses main-study participants run under different config hashes.

If only one laptop runs sessions, leave `STATION_SEQUENCES` empty: that laptop then uses all sequences.

**One laptop, researcher monitor on a phone:** run `python manage.py runserver 0.0.0.0:8000`, add the laptop's IP (from `ipconfig`) to `DJANGO_ALLOWED_HOSTS`, and open `http://<ip>:8000/researcher/` on a phone on the same Wi-Fi. See `docs/PILOT_DAY_CHECKLIST.md`.

## 7. Documents

- `docs/AUDIT_AND_PLAN.md`: design audit (4 Nov 2026), what changed and why, and the plan to the main study.
- `docs/PILOT_DAY_CHECKLIST.md`: step-by-step for pilot sessions, with what to observe.
- `docs/materials/Questionnaires.md`: every item exactly as shown in the app.
- `docs/materials/Consent_form_v2.md`: consent form matching the app (fill in retention period and contacts).

## 8. Claude API: cost, limits and settings

- **Provider.** The app uses the Claude API by default (`LLM_PROVIDER=anthropic`). Gemini still works if you set `LLM_PROVIDER=gemini`, but use one provider for all pilots and the main study.
- **Cost.** A full session makes roughly 30-45 calls (about 60,000 input and 5,000 output tokens). For the whole study, including pilots and blind scoring, expect a few dollars with Sonnet and well under one dollar with Haiku. `pilot_system --runs 1` makes up to about 300 calls, so it is the most expensive single command.
- **Set a spending limit** in the Claude Console (Settings > Limits) before you start, so a mistake in a loop cannot run up a bill.
- **Rate limits** depend on your account's usage tier and are shown in the Console. A single session is far below them. If a call fails, the app retries twice, then asks the participant to resend and flags the monitor.
- **Pin the model.** Put one exact model ID in `LLM_MODEL`, record it in the paper, and do not change it after pilot P4.
- **Speed.** The pilot target is replies in 4 seconds or less. `LLM_EFFORT=low` keeps replies quick. `pilot_system` reports median latency; if Sonnet is too slow, compare Haiku in P1 before deciding.
- **No temperature.** The current Claude API has no temperature setting (the `TEMP_*` values apply only to Gemini). The judge and scorer instead return scores through a fixed JSON schema (structured outputs), and the scorer still runs three times and keeps the median. Update the paper's System paragraph, which mentions temperatures.
- **Keep the key private.** Never commit `.env` (it is in `.gitignore`) and do not share the key in group chats.

## 9. Tests

```bash
LLM_MOCK=1 python manage.py test study
```

Covers the adaptive rule, counterbalancing balance, STAI scoring, a complete participant session, the high-stress alert, pilot ID separation, two-laptop station split and bundle round trip, stopping and skipping rounds, the reflection note, the tag screen context, and that no level prompt repeats the probe wording.

On Windows PowerShell: `$env:LLM_MOCK="1"; python manage.py test study; Remove-Item Env:LLM_MOCK`

## Notes

- Participant links are `/s/<ID>/`. This is meant for running on a lab laptop or local network, not the open internet.
- The STAI-6 items follow Marteau & Bekker (1992); check the STAI licence terms with your advisor before use.
