"""M6 — Jog engine configuration (locked constants)."""
from datetime import date

TODAY = "2026-10-06"
LIBRARY_END = "2026-09-28"

W_VISUAL = 0.50
W_TIME = 0.20
W_PLACE = 0.20
W_ATTR = 0.10

CERTAINTY = {"sure": 1.0, "unsure": 0.5}
TOP_K = 40
SOFTMAX_T = 0.08
MAX_ROUNDS = 4
MOMENT_GAP_HOURS = 8
MOMENT_MAX_KM = 10

# answerability priors: probability a user "knows" the attribute for a random photo
PRIORS = {
    "indoor_outdoor": 0.9,
    "time_of_day": 0.8,
    "place_name": 0.8,
    "setting_type": 0.7,
    "season_hint": 0.6,
    "people_count_bucket": 0.5,
    "has_text": 0.5,
    "dominant_color": 0.4,
}

REL_FEEDBACK = {"alpha": 1.0, "beta": 0.6, "gamma": 0.3}

TIME_DECAY_DAYS = 60
UNSURE_WIDEN_DAYS = 30
PLACE_KM = 25

CUE_TYPES = ["place", "time_window", "person", "object", "activity", "setting_type",
             "visual_detail", "time_of_day", "indoor_outdoor", "season", "anchor_event",
             "purpose", "text_in_image", "emotion"]
QUERY_STYLES = ["keyword", "natural_language", "date_or_filter", "people_or_face",
                "map_or_place", "browse_scroll", "ask_photos_chat", "none_stated"]
WORKAROUNDS = ["scroll_timeline", "search_other_app", "ask_other_person",
               "manual_albums_or_favorites", "rename_or_describe", "use_other_service",
               "switch_to_classic_search", "gave_up", "none_stated"]
OUTCOMES = ["found", "partly_found", "not_found", "unknown"]
