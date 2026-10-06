# R1 Item 7 — Codebook (interview data ↔ discovery engine)

Use these enums when logging so interviews compare directly with the discovery engine's episodes.

## cue_type (what a person remembers about a photo)
| enum | one-line definition | example |
|---|---|---|
| person | who is in it | "my cousin was in it" |
| place | where it was taken | "it was in Hampi" |
| time_when | when it was taken | "last December", "before the exams" |
| event_context | the event/occasion | "it was at my birthday" |
| anchor_relation | defined relative to another moment | "the day after we went to the beach" |
| visual_detail | a visible detail | "there was a yellow umbrella" |
| setting | kind of place/scene | "it was in a café" |
| activity | what was happening | "we were cycling" |
| emotion_or_vibe | how it felt | "it was such a happy day" |
| purpose_or_reason | why it was taken | "I took it to remember the dosage" |
| text_in_image | readable text in it | "the receipt had the order number" |
| source | where it came from | "someone sent it in WhatsApp" |
| device_or_app | which device/app | "I took it on my old phone" |
| other | anything else stated | — |

## certainty
- sure = stated firmly ("it was…")
- think so = hedged ("I think…", "maybe…")

## failure_gate (where the retrieval attempt broke)
| enum | definition | example |
|---|---|---|
| expression | user cannot turn memory into a query | "I know it's there but I can't say how to search for it" |
| interpretation | the system ignores or misreads the clues given | "I typed 'Hampi' and it showed my office photos" |
| evaluation | right photo may be among results but user cannot recognize/compare, too many similar, or too slow | "it showed 200 sunsets, I couldn't tell which was which" |
| refinement | first attempt failed and no effective way to adjust or recover | "nothing came up and I didn't know what else to try" |
| persistence | user gave up or no longer searches | "I stopped searching, I just don't use it anymore" |
| not_search_related | sync/backup/deletion/storage problem, not a search attempt | "my photos just disappeared after the update" |
| unclear | cannot tell from the account | — |

## query_style (how they searched)
| enum | definition |
|---|---|
| keyword | short words in the search box |
| natural_language | a full sentence |
| date_or_filter | date range / filters / sort |
| people_or_face | the face/people tab |
| map_or_place | the map or a place name |
| browse_scroll | scrolling the timeline, no search |
| ask_photos_chat | the Ask tab / Ask Photos |
| none_stated | did not say |

## workaround (what they do after search fails)
scroll_timeline · search_other_app · ask_other_person · manual_albums_or_favorites · rename_or_describe · use_other_service · switch_to_classic_search · gave_up · none_stated

## outcome
found · partly_found · not_found · unknown

## photo_type
trip_event · people_social · food_place · scenery_pet · document_utility · screenshot · video · other_unspecified
