"""
Generate the SIMULATED participant study (R2-sim).

Six LLM-authored participant profiles run through the exact R1 interview
protocol (sections A-E + reverse-recall probe). PURPOSE: validate the
interview kit end-to-end, check codebook coverage, and generate candidate
retrieval scenarios. CONSTRAINT (integrity): this is NOT real user evidence.
It must be labelled "simulated" everywhere and never cited in the deck as
user quotes. Real evidence = discovery data + friend probe videos (solo
think-aloud protocol, research/interview_kit/solo_video_protocol.md).

Outputs:
  research/sim/README.md
  research/sim/P{i}_sim.md  (6 transcripts, protocol order)
  research/notes_simulated.csv  (exact R1 note-sheet schema)
"""
import csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "research" / "sim"

PARTICIPANTS = [
    dict(
        pid="P1", label="P1 (simulated)",
        segment_flags="years_of_use=4; library_size_est=~18,000; device=Android (Pixel 7a); auto_backup=yes; segment=target",
        relationship="friend",
        profile="20, third-year B.Tech (CSE) at a Goa campus, lives in a PG near the campus. Heavy photo user; screenshots everything.",
        context="Uses Google Photos 4 years, backup on since first phone. About 18,000 photos and videos. Android, backup automatic.",
        incident_story=("A screenshot of a train ticket (Mumbai-Pune, summer 2024). A college form asked for the "
                        "travel date and he could not remember it. He knew the screenshot existed. He typed "
                        "'train ticket' and got a pile of similar ticket screenshots, then added 'mumbai pune', "
                        "then filtered by 2024, then opened results one by one until the dates matched. "
                        "Found it in about 4 minutes. Did not use the Ask tab."),
        incident_cues_remembered="device_or_app|it was a screenshot|sure; text_in_image|train ticket, MUMBAI to PUNE|sure; time_when|summer 2024|think so; purpose_or_reason|to keep the travel date|sure",
        incident_cues_missing="exact date; which phone it was taken on",
        first_action="typed 'train ticket' in Google Photos search",
        incident_queries="train ticket; mumbai pune; 2024",
        incident_reformulation_count="2",
        incident_workaround="date filter, then opened similar results one by one to compare",
        incident_outcome="found",
        probe_photo_age_months="30",
        probe_story=("Chose a hostel fest photo from about 30 months ago (March 2023): the stage during a band "
                     "night, taken from the back of the crowd. Described it to the interviewer first, then "
                     "screen-shared. Typed 'fest' (too many results), then 'band' (still many), then used the "
                     "date filter for March 2023 and found it. 95 seconds total. Success."),
        probe_cues="place|hostel fest stage|sure|correct; event_context|band performance at fest|sure|correct; visual_detail|stage with blue lights|sure|wrong; time_when|march, winter break|think so|correct; person|me and Rohan were there|sure|wrong",
        probe_queries="fest; band; march 2023",
        probe_reformulations="2",
        probe_time_to_find_s="95",
        probe_success="Y",
        probe_used_ask_tab="no",
        forgotten_after_reveal="visual_detail|stage with blue lights|wrong (red and blue); person|me and Rohan were there|wrong (Rohan was not in frame)",
        expectation_confidence_1to5="4",
        ease_1to7="5",
        workarounds_mentioned="ask friends to resend; check Instagram stories; scroll timeline month by month",
        quote="I always remember the feeling, never the date.",
        observed=("Typed 3 queries, all single keywords; reformulations added new info (place, then date). "
                  "Compared ~8 similar ticket screenshots one by one in the incident. Verbatim: 'I always "
                  "remember the feeling, never the date.'"),
    ),
    dict(
        pid="P2", label="P2 (simulated)",
        segment_flags="years_of_use=2; library_size_est=~9,000; device=iPhone 13; auto_backup=yes; segment=target",
        relationship="friend",
        profile="21, B.Des student in Pune, commutes by train. Moderate photo user; takes few photos, keeps screenshots of useful things.",
        context="Google Photos for 2 years, auto backup. Around 9,000 photos. iPhone.",
        incident_story=("A medicine photo from December 2025 (sick week): she had photographed the medicine strip "
                        "and the prescription so she would remember the dosage. Typed 'medicine' and found it on "
                        "the first search. Found in under a minute. No Ask tab use."),
        incident_cues_remembered="purpose_or_reason|to remember the dosage|sure; text_in_image|medicine strip and prescription|sure; time_when|december, when i was sick|think so",
        incident_cues_missing="exact medicine name in the text",
        first_action="typed 'medicine' in Google Photos search",
        incident_queries="medicine",
        incident_reformulation_count="0",
        incident_workaround="none needed",
        incident_outcome="found",
        probe_photo_age_months="34",
        probe_story=("Chose a Diwali sweets photo from home, November 2023 (~34 months). Did not type anything: "
                     "went straight to the timeline and scrolled to November 2023, found it among the Diwali "
                     "photos. 70 seconds. Success, first try."),
        probe_cues="event_context|diwali at home|sure|correct; visual_detail|sweets and diya on the table|sure|correct; place|pune, at home|sure|correct; time_when|november|think so|correct",
        probe_queries="",
        probe_reformulations="0",
        probe_time_to_find_s="70",
        probe_success="Y",
        probe_used_ask_tab="no",
        forgotten_after_reveal="setting|shot in the living room|wrong (dining table)",
        expectation_confidence_1to5="5",
        ease_1to7="6",
        workarounds_mentioned="scroll to the month; auto-albums (a Food album helped once); ask her mother",
        quote="I don't search, I just scroll to the month.",
        observed=("Zero queries in the probe: pure browse_scroll strategy. Relies on the timeline + auto-albums. "
                  "Verbatim: 'I don't search, I just scroll to the month.'"),
    ),
    dict(
        pid="P3", label="P3 (simulated)",
        segment_flags="years_of_use=3.5; library_size_est=~32,000; device=Android (Samsung A54); auto_backup=yes; segment=target",
        relationship="acquaintance",
        profile="22, final-year B.Tech, very heavy photo user (camera on almost every day). Big library, few albums.",
        context="3.5 years, about 32,000 photos, Android Samsung, backup automatic since year one.",
        incident_story=("A whiteboard photo from a group-project presentation (Jan 2025): he had photographed the "
                        "board with equations to revise later. Needed it the week before exams. Typed "
                        "'whiteboard', got a mix of board + notes photos, then 'whiteboard equations' - still could "
                        "not tell which one was the right presentation. Gave up that day and photocopied from a "
                        "teammate's notes instead. Not found."),
        incident_cues_remembered="visual_detail|whiteboard with equations|sure; setting|classroom, group presentation|sure; time_when|before winter break, january|think so; purpose_or_reason|to revise before exams|sure",
        incident_cues_missing="which subject/group it was for; the exact slide on the board",
        first_action="typed 'whiteboard' in Google Photos search",
        incident_queries="whiteboard; whiteboard equations",
        incident_reformulation_count="1",
        incident_workaround="got the content from a teammate's notes instead of the photo",
        incident_outcome="not_found",
        probe_photo_age_months="27",
        probe_story=("Chose a Hampi trip photo (~27 months, Sept 2023): a river photo with big rocks. Typed "
                     "'hampi boat', saw 3 similar river shots, picked the wrong one first (no ruins in background), "
                     "then 'hampi ruins boat' and found the right one. 130 seconds. Success after one wrong pick."),
        probe_cues="place|hampi|sure|correct; visual_detail|big rocks and a boat on the river|sure|wrong; time_when|after monsoon, september|think so|wrong; person|with four friends|think so|unverifiable",
        probe_queries="hampi boat; hampi ruins boat",
        probe_reformulations="1",
        probe_time_to_find_s="130",
        probe_success="Y",
        probe_used_ask_tab="no",
        forgotten_after_reveal="visual_detail|boat on the river|wrong (coracle, he remembered a motorboat); time_when|afternoon|wrong (evening)",
        expectation_confidence_1to5="4",
        ease_1to7="4",
        workarounds_mentioned="check WhatsApp chats with trip friends; trip albums; ask the travel buddy",
        quote="The photo exists, my brain just has the wrong version of it.",
        observed=("Reformulation added discriminating info ('ruins'). One wrong pick verified by looking at the "
                  "background. Incident = explicit give-up after 2 queries (refinement). Verbatim: 'The photo "
                  "exists, my brain just has the wrong version of it.'"),
    ),
    dict(
        pid="P4", label="P4 (simulated)",
        segment_flags="years_of_use=1; library_size_est=~2,500; device=iPhone 12; auto_backup=yes; segment=boundary (light user)",
        relationship="friend",
        profile="20, first-year BSc, hostel. Light user: few photos, heavy reliance on the People/face feature.",
        context="Google Photos just over a year, about 2,500 photos, iPhone 12.",
        incident_story=("A screenshot of a bus timetable (June 2025) she needed to check a route. Typed 'timetable' "
                        "- no results (the text inside the screenshot was not found). Typed 'bus' - the screenshot "
                        "appeared in results. Found on the second try. Never used Ask Photos knowingly."),
        incident_cues_remembered="text_in_image|bus timetable with the route number|sure; purpose_or_reason|to check the route later|sure; time_when|this year|think so",
        incident_cues_missing="the exact route number from memory",
        first_action="typed 'timetable' in Google Photos search",
        incident_queries="timetable; bus",
        incident_reformulation_count="1",
        incident_workaround="none (second keyword worked)",
        incident_outcome="found",
        probe_photo_age_months="12",
        probe_story=("Chose a family Diwali photo from home (Nov 2024, ~12 months). Did not type anything: opened "
                     "the People tab, tapped her mother's face, and the photo was in the face grid. 25 seconds. "
                     "Success, first action."),
        probe_cues="person|my mother and father|sure|correct; event_context|diwali at home|sure|correct; place|pune|sure|correct",
        probe_queries="",
        probe_reformulations="0",
        probe_time_to_find_s="25",
        probe_success="Y",
        probe_used_ask_tab="not stated",
        forgotten_after_reveal="person|I was in the photo|wrong (she was behind the camera)",
        expectation_confidence_1to5="5",
        ease_1to7="7",
        workarounds_mentioned="People/face feature first; ask family; albums",
        quote="Typing never finds it, faces always do.",
        observed=("Zero typing in the probe: people_or_face strategy. Incident shows screenshot text not being "
                  "searchable (interpretation). Verbatim: 'Typing never finds it, faces always do.'"),
    ),
    dict(
        pid="P5", label="P5 (simulated)",
        segment_flags="years_of_use=4; library_size_est=~28,000; device=Android (Pixel 8); auto_backup=yes; segment=target",
        relationship="friend",
        profile="23, graduated last year, worked in Bengaluru for a year (intern then full-time). Photos a lot of work things.",
        context="4+ years, about 28,000 photos, Android Pixel 8.",
        incident_story=("A photo of meeting notes on a sticky note from a client meeting (July 2025): he needed the "
                        "client's domain name written on it. Typed 'sticky note', got ~6 similar notes photos, "
                        "could not read the small text in thumbnails, opened five of them one by one until the "
                        "name matched. Found in about 6 minutes. No Ask tab."),
        incident_cues_remembered="text_in_image|the client's domain name on it|sure; purpose_or_reason|work reference|sure; setting|office meeting|sure; time_when|around july 2025|think so",
        incident_cues_missing="the exact domain name from memory",
        first_action="typed 'sticky note' in Google Photos search",
        incident_queries="sticky note",
        incident_reformulation_count="0",
        incident_workaround="opened results one by one and read the text in each",
        incident_outcome="found",
        probe_photo_age_months="15",
        probe_story=("Chose a rooftop dinner photo from the end of his internship (July 2025, ~15 months): the "
                     "night after a team offsite. Typed 'rooftop' (20+ results), then date filter July 2025 "
                     "(3 candidates), found it. 110 seconds. Success."),
        probe_cues="anchor_relation|the night after the team offsite|think so|wrong; place|bengaluru|sure|correct; setting|rooftop at night|sure|correct; person|our team, about eight people|think so|wrong",
        probe_queries="rooftop; july 2025",
        probe_reformulations="1",
        probe_time_to_find_s="110",
        probe_success="Y",
        probe_used_ask_tab="no",
        forgotten_after_reveal="anchor_relation|the night after the offsite|wrong (two nights after); person|about eight people|wrong (six)",
        expectation_confidence_1to5="3",
        ease_1to7="4",
        workarounds_mentioned="screenshots of everything now; ask teammates to resend",
        quote="I remember the story, not the photo.",
        observed=("Reformulation added a date window (date_or_filter). Anchor memory was off by one night. "
                  "Verbatim: 'I remember the story, not the photo.'"),
    ),
    dict(
        pid="P6", label="P6 (simulated)",
        segment_flags="years_of_use=2.5; library_size_est=~12,000; device=Android (Redmi); auto_backup=yes; segment=target",
        relationship="friend",
        profile="21, second-year, hostel. Social photographer: group shots, trips, food. Struggles with near-duplicates.",
        context="2.5 years, about 12,000 photos, Android Redmi, backup automatic.",
        incident_story=("A group photo from fest week (Feb 2025) she wanted to repost on Instagram. Typed "
                        "'corridor' - nothing. Typed 'fest group' - 15 similar group photos, could not tell which. "
                        "Gave up on searching and asked a friend to resend it on WhatsApp. Not found via search."),
        incident_cues_remembered="person|five of us friends|sure; event_context|fest week, hostel corridor|sure; visual_detail|string lights in the background|think so",
        incident_cues_missing="which exact night of fest week; who else was in the frame",
        first_action="typed 'corridor' in Google Photos search",
        incident_queries="corridor; fest group",
        incident_reformulation_count="1",
        incident_workaround="asked a friend to resend it on WhatsApp",
        incident_outcome="not_found",
        probe_photo_age_months="21",
        probe_story=("Chose 'the sunset with a boat' (~21 months). Was unsure whether it was the Goa trip (Jan "
                     "2024) or Gokarna (Jan 2025) - both had sunsets with boats. Typed 'boat sunset' (6 similar), "
                     "'gokarna' (3), 'goa' (3). Picked the 2024 one, checked the date, realised it was the old "
                     "trip, but ran out of time at the 5-minute stop with two candidates left. Partial success."),
        probe_cues="visual_detail|sunset with a boat in the foreground|sure|correct; place|goa or gokarna, i think|think so|wrong; time_when|around new year|think so|correct; emotion_or_vibe|we stood there a long time, it felt special|think so|unverifiable",
        probe_queries="boat sunset; gokarna; goa",
        probe_reformulations="2",
        probe_time_to_find_s="300",
        probe_success="partial",
        probe_used_ask_tab="no",
        forgotten_after_reveal="place|goa|wrong (it was Gokarna); visual_detail|a wooden boat|wrong (white fishing boat)",
        expectation_confidence_1to5="3",
        ease_1to7="2",
        workarounds_mentioned="ask the person who was with me; Instagram archive; albums by trip (she made none)",
        quote="Two almost-same sunsets, and my brain deleted the difference.",
        observed=("Reformulations swapped place keywords, added no new discriminating cue (the distinguishing "
                  "detail was never stated). Stopped at 5-minute limit with 2 candidates (partial). Verbatim: "
                  "'Two almost-same sunsets, and my brain deleted the difference.'"),
    ),
]

CSV_COLS = ["participant_id","date","segment_flags","relationship","incident_photo_type",
            "incident_cues_remembered","incident_cues_missing","first_action","incident_queries",
            "incident_reformulation_count","incident_workaround","incident_outcome","probe_photo_age_months",
            "probe_cues","probe_queries","probe_reformulations","probe_time_to_find_s","probe_success",
            "probe_used_ask_tab","forgotten_after_reveal","expectation_confidence_1to5","ease_1to7",
            "workarounds_mentioned","notable_quote_verbatim","observed_behavior_notes"]

INCIDENT_TYPE = {"P1": "screenshot", "P2": "document_utility", "P3": "document_utility",
                 "P4": "screenshot", "P5": "document_utility", "P6": "people_social"}


def render_transcript(p):
    return f"""# {p['label']} — SIMULATED interview transcript

> **SIMULATED PARTICIPANT.** Profile and answers were generated by an AI model for protocol
> validation and scenario generation. NOT a real person. Do not cite as user evidence.

- Profile: {p['profile']}
- Relationship (if real): {p['relationship']} (simulated)

## OPENING (consent)
Consent script read; participant agrees; audio recording consent: yes (simulated). Participant code {p['pid']}.

## A — Context
{p['context']}

## B — Critical incident (last time searching)
Incident photo type: {INCIDENT_TYPE[p['pid']]}.

{p['incident_story']}

Cues remembered (as logged): {p['incident_cues_remembered']}
Cues missing: {p['incident_cues_missing']}
First action: {p['first_action']}
Queries in order: {p['incident_queries'] or 'none'}
Reformulations: {p['incident_reformulation_count']}
Workaround: {p['incident_workaround']}
Outcome: {p['incident_outcome']}
Ask tab used for incident: no

## C — Reverse-recall probe (photo ~{p['probe_photo_age_months']} months old)
{p['probe_story']}

Cues stated before searching (type|value|certainty): {p['probe_cues']}
Queries in order: {p['probe_queries'] or 'none (no typing)'}
Reformulations: {p['probe_reformulations']}
Time to find (s): {p['probe_time_to_find_s']}
Success: {p['probe_success']}
Used Ask tab: {p['probe_used_ask_tab']}

Cue audit after reveal (type|value|verdict): {p['forgotten_after_reveal']}
Confidence before (1-5): {p['expectation_confidence_1to5']}
Ease after (1-7): {p['ease_1to7']}

## D — Workarounds & expectations
Workarounds mentioned: {p['workarounds_mentioned']}

## E — Wrap-up
Notable verbatim quote: "{p['quote']}"

## Interviewer notes (observed, not reported)
{p['observed']}
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in PARTICIPANTS:
        (OUT / f"{p['pid']}_sim.md").write_text(render_transcript(p))
    rows = []
    for p in PARTICIPANTS:
        row = {c: p.get(c, "") for c in CSV_COLS}
        row["participant_id"] = p["pid"]
        row["date"] = "2026-10-06 (simulated)"
        row["incident_photo_type"] = INCIDENT_TYPE[p["pid"]]
        row["notable_quote_verbatim"] = p["quote"]
        rows.append(row)
    with open(BASE / "research" / "notes_simulated.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(PARTICIPANTS)} transcripts + notes_simulated.csv")


if __name__ == "__main__":
    main()
