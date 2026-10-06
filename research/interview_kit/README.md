# R1 Interview kit — how to run it (for the user and the friend-interviewers)

1. **Create the Google Form** from `screener_form.md` (BITS account). Keep responses private.
2. **Create a private Google Sheet** with the columns in `note_sheet.md` (2 tabs: raw, anonymized).
3. **Send the recruiting message** (`recruitment_message.txt`, <70 words) with the form link, per `recruiting_plan.md`.
4. **Send each friend-interviewer** (college student, Goa):
   - `interviewer_script_friend.md` — read it start-to-finish, verbatim boxes.
   - `codebook.md` — the cue types and labels they must use while logging.
   - `notes_template.csv` — the row format to fill after each call.
   - Consent is already spoken inside the script's OPENING block (also in `consent_script.md`).
5. After each call the friend fills their Note Sheet row and sends it over; you keep the master.
6. When all 6 are done: export the Note Sheet to `BASE/research/notes.csv` and run R2
   (`code/synthesis_r2.py`) for the synthesis.

## Files
| file | what it is |
|---|---|
| interviewer_script_friend.md | the verbatim script a friend reads (the main deliverable) |
| screener_form.md | Google Form spec + acceptance rules |
| recruitment_message.txt | WhatsApp message (<70 words) |
| consent_script.md | spoken consent (<90 s) |
| interview_guide.md | researcher's master guide with timings |
| reverse_recall_probe_protocol.md | the exact 5-step probe |
| note_sheet.md + notes_template.csv | the note sheet spec + CSV template |
| codebook.md | enums shared with the discovery engine |
| logistics.md | call/recording/privacy logistics |
| recruiting_plan.md | how to get 6 participants in 24 h |
