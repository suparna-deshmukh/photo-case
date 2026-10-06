# R1 Item 6 — Note sheet (columns for the researcher's Google Sheet; private)

Create a private Google Sheet with tab "raw" (these columns) and a second tab "anonymized"
(everything except: date, relationship, workarounds_mentioned, notable_quote_verbatim with names removed).

| column | notes |
|---|---|
| participant_id | P1…P6 |
| date | interview date |
| segment_flags | years_of_use; library_size_est; device (e.g. "3+yrs; 10k+; android") |
| relationship | friend / acquaintance / stranger (limitation note) |
| incident_photo_type | trip_event / people_social / food_place / scenery_pet / document_utility / screenshot / video / other_unspecified |
| incident_cues_remembered | `type\|value\|certainty; type\|value\|certainty` |
| incident_cues_missing | forgotten cues, free text |
| first_action | what they typed/tapped first (exact words) |
| incident_queries | exact queries, order |
| incident_reformulation_count | int |
| incident_workaround | what else they did |
| incident_outcome | found / partly_found / not_found / gave_up / unknown |
| probe_photo_age_months | int (>=24) |
| probe_cues | `type\|value\|certainty\|verified` rows |
| probe_queries | exact, in order |
| probe_reformulations | int |
| probe_time_to_find_s | seconds from first tap (blank if no success) |
| probe_success | Y / N / partial |
| probe_used_ask_tab | Y / N |
| forgotten_after_reveal | cues marked wrong/forgotten in Step 4 |
| expectation_confidence_1to5 | int |
| ease_1to7 | int |
| workarounds_mentioned | list, their words |
| notable_quote_verbatim | ONE exact sentence (verified later as substring of notes) |
| observed_behavior_notes | what they DID, not what they said |
