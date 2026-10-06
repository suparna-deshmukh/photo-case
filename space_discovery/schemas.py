"""
Purpose: D6 - shared pydantic v2 models for the LLM extraction pipeline.
         Single source of truth for the Episode schema used by run_stage1.py,
         run_stage2.py, the D6 pilot, D7 validation, and the D10 app layer.
Inputs : none (definitions only).
Outputs: Gate, Cue, Episode, Stage1Screen pydantic models.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel

Gate = Literal["expression", "interpretation", "evaluation", "refinement", "persistence", "not_search_related", "unclear"]


class Cue(BaseModel):
    type: Literal["person", "place", "time_when", "event_context", "anchor_relation",
                  "visual_detail", "setting", "activity", "emotion_or_vibe",
                  "purpose_or_reason", "text_in_image", "source", "device_or_app", "other"]
    value: str
    certainty: Literal["high", "medium", "low"]


class Episode(BaseModel):
    is_retrieval_episode: bool
    retrieval_intent: Optional[Literal["find_specific_photo", "find_set_or_moment",
                                       "find_info_inside_photo", "find_by_person", "other"]] = None
    photo_type: Optional[Literal["trip_event", "people_social", "food_place", "scenery_pet",
                                 "document_utility", "screenshot", "video", "other_unspecified"]] = None
    photo_age: Optional[Literal["recent_lt_6m", "six_to_24m", "over_2y", "unspecified"]] = None
    remembered_cues: List[Cue] = []
    missing_cue_types: List[str] = []
    query_attempted: Optional[str] = None
    query_style: Optional[Literal["keyword", "natural_language", "date_or_filter", "people_or_face",
                                  "map_or_place", "browse_scroll", "ask_photos_chat", "none_stated"]] = None
    failure_gate: Optional[Gate] = None
    failure_mechanism: Optional[str] = None   # <= 15 words, plain description of WHY it failed
    workaround: Optional[Literal["scroll_timeline", "search_other_app", "ask_other_person",
                                 "manual_albums_or_favorites", "rename_or_describe", "use_other_service",
                                 "switch_to_classic_search", "gave_up", "none_stated"]] = None
    stakes: Optional[Literal["low", "medium", "high"]] = None
    outcome: Optional[Literal["found", "partly_found", "not_found", "unknown"]] = None
    evidence_quote: Optional[str] = None      # verbatim, <= 200 chars
    confidence: float = 0.0


class Stage1Screen(BaseModel):
    relevant_ids: List[str] = []
