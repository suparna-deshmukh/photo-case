"""Single source of truth for every user-visible string.

Revamp brief section 6 (copy deck) + contract-locked test-mode strings.
All tests and UI code import from here — never hard-code a user-facing string.
"""

# ---------- helpers ----------
def plural(n, word="photo"):
    return f"{n} {word if n == 1 else word + 's'}"

def day(d):
    """'Sat, 25 Oct 2025' from a date-like value."""
    import pandas as pd
    t = pd.to_datetime(d)
    return t.strftime("%a, %-d %b %Y")

def short_day(d):
    import pandas as pd
    return pd.to_datetime(d).strftime("%-d %b")

def daterange(d0, d1):
    """'22–28 Oct 2025' (same month) or '28 Dec 2025 – 2 Jan 2026'."""
    import pandas as pd
    a, b = pd.to_datetime(d0), pd.to_datetime(d1)
    if a.date() == b.date():
        return a.strftime("%-d %b %Y")
    if a.year == b.year and a.month == b.month:
        return f"{a.day}\u2013{b.day} {a.strftime('%b %Y')}"
    if a.year == b.year:
        return f"{a.strftime('%-d %b')} \u2013 {b.strftime('%-d %b %Y')}"
    return f"{a.strftime('%-d %b %Y')} \u2013 {b.strftime('%-d %b %Y')}"

# ---------- shell / nav ----------
APP_NAME = "Photos"
NAV_PHOTOS = "Photos"
NAV_COLLECTIONS = "Collections"
NAV_PEOPLE = "People"
NAV_PLACES = "Places"
AVATAR_MENU = ("About this demo", "How Ask Photos works", "Start over")
DEMO_CHIP = "Demo"
DEMO_NOTICE = ("Demo library: every photo is freely licensed, and every date, "
               "place and person is synthetic.")

# ---------- search ----------
SEARCH_PLACEHOLDER = "Search your photos"
BTN_SEARCH = "Search"
TOGGLE_SEARCH = "Search"
TOGGLE_ASK = "Ask"
SUG_PEOPLE = "People"
SUG_PLACES = "Places"
SUG_THINGS = "Things"
SUG_YEARS = "Years"
RESULTS_HEADER = "Results for \u201c{q}\u201d"
NUDGE_TITLE = "Not quite right?"
NUDGE_TEXT = "Describe it in a sentence and I'll help narrow it down."
BTN_ASK_PHOTOS = "Ask Photos"
ZERO_TITLE = "No close matches"
ZERO_TEXT = "Nothing looks like \u201c{q}\u201d yet. Describe the photo in a sentence and I'll help narrow it down."
BTN_SHOW_ANYWAY = "Show closest photos anyway"
GROUP_PEOPLE = "People"
GROUP_PEOPLE_SUB = "in these results"
GROUP_PLACES = "Places"
GROUP_PLACES_SUB = "where these were taken"
IN_RESULTS = "{n} in results"
SEE_ALL = "See all"

# ---------- Ask Photos ----------
ASK_TITLE = "Ask Photos"
ASK_SUBTITLE = ("Describe a photo you half-remember. I'll show likely matches, "
                "then ask a couple of quick questions.")
ASK_PLACEHOLDER = "e.g. a caf\u00e9 somewhere in Goa, daytime I think, coffee before the beach"
ASK_HELPER = "Add a few details: a place, a time of year, or what was happening."
BTN_FIND = "Find it"
PRIVACY_AI = "Your description is processed by {provider} to understand it. Please don't include personal details."
PRIVACY_OFFLINE = "Your description is processed inside this demo and isn't sent anywhere."
LOADING = "Looking through {n} photos\u2026"
PICKED_UP = "Here's what I picked up"
CHIP_HINT = "Tap a chip to correct it"
CHIP_MENU = ("That's right", "Not sure", "Not this", "Remove")
NO_CUES = "No details detected \u2014 using visual similarity."
QUESTION_LABEL = "Quick question"
OPT_INDOORS = "Indoors"
OPT_OUTDOORS = "Outdoors"
OPT_UNSURE = "Not sure"
OPT_MORNING = "Morning"
OPT_AFTERNOON = "Afternoon"
OPT_EVENING = "Evening"
OPT_NIGHT = "Night"
OPT_SETTING_CAFE = "Caf\u00e9"
OPT_SETTING_BEACH = "Beach"
OPT_SETTING_STREET = "Street"
OPT_SETTING_CAMPUS = "Campus"
OPT_SETTING_HOME = "Home"
OPT_SETTING_RESTAURANT = "Restaurant"
OPT_SETTING_TEMPLE = "Temple or ruins"
OPT_SETTING_NATURE = "Nature"
OPT_SETTING_TRANSPORT = "Transport"
OPT_SETTING_PARTY = "Party or event"
OPT_SETTING_MARKET = "Shop or market"
OPT_SETTING_DOCUMENT = "Document or receipt"
OPT_SETTING_OTHER = "Somewhere else"
OPT_SEASON_SUMMER = "Summer"
OPT_SEASON_MONSOON = "Monsoon"
OPT_SEASON_WINTER = "Winter"
OPT_PEOPLE_NONE = "Just me"
OPT_PEOPLE_ONE = "One other person"
OPT_PEOPLE_FEW = "A few people"
OPT_PEOPLE_GROUP = "A group"
OPT_WRITING_YES = "Yes"
OPT_WRITING_NO = "No"
SKIP = "I don't remember"
STATUS_MATCHES = "{n} likely matches"
STATUS_MATCHES_RANGE = "{n} likely matches around {range}"
SHOW_MORE_DATES = "Show more dates"
SEE_ALL_N = "See all {n}"
SEARCH_AROUND_DATE = "Search around this date"
BTN_BROWSE_DATE = "Browse by date"
BTN_BROWSE_DATE_RANGE = "Browse by date ({range})"
BTN_START_OVER = "Start over"
FALLBACK_TITLE = "I'd narrow it to {range}"
FALLBACK_SUB = "Pick a day to browse, or start over."
DAY_CHIP = "{day} \u00b7 {n} photos"

# ---------- questions (engine attribute -> text) ----------
Q_INDOOR_OUTDOOR = "Was it indoors or outdoors?"
Q_TIME_OF_DAY = "What time of day was it?"
Q_SETTING = "What kind of place was it?"
Q_SEASON = "Which season was it?"
Q_PEOPLE = "How many people were in it?"
Q_WRITING = "Was there any writing in the photo?"
Q_PLACE = "Which place?"
Q_PERSON = "Was this with {a} or {b}?"

# ---------- lightbox ----------
LB_THATS_IT = "That's it"
LB_CLOSE_NOT_IT = "Close, but not it"
LB_SHARE = "Share"
LB_DETAILS = "Details"
LB_PREV = "Previous"
LB_NEXT = "Next"
LB_CLOSE = "Close"
LB_POSITION = "{i} of {n}"
TOAST_NARROWED = "Narrowed to 3 days around that photo."
TOAST_LINK_COPIED = "Link copied (demo)."
TOAST_UPDATED = "Updated"
BTN_UNDO = "Undo"
TOAST_THANKS = "Thanks \u2014 that helps."
DETAILS_SYNTHETIC = "Synthetic demo data"

# ---------- anchor sheet ----------
ANCHOR_TITLE = "The photo I'm after was\u2026"
ANCHOR_SAME_DAY = "On the same day"
ANCHOR_AFTER = "A few days later"
ANCHOR_BEFORE = "A few days earlier"
ANCHOR_AROUND = "Around that time"

# ---------- success ----------
SUCCESS_FOUND_IN = "Found it in {t}"
SUCCESS_STEPS = "{k} steps"
BTN_SEARCH_ANOTHER = "Search another"
SUCCESS_RIGHT_PHOTO = "Was this the right photo?"
YES = "Yes"
NO = "No"

# ---------- collections ----------
COLL_PEOPLE = "People"
COLL_PLACES = "Places"
COLL_PEOPLE_EMPTY = "No people found yet."
WHICH_IS_YOU = "Which one is you?"
WHICH_IS_YOU_SUB = "Pick yourself and we'll recognise your photos."
THIS_IS_ME = "This is me"
NOT_SURE = "Not sure"
YOU = "You"
PHOTOS_OF = "{n} photos"

# ---------- resume card ----------
RESUME_TITLE = "Pick up where you left off"
RESUME_QUERY = "Your search: \u201c{q}\u201d"
BTN_CONTINUE = "Continue"

# ---------- home ----------
HOME_TITLE = "Your photos"
HOME_MEMORIES = "Memories"
MONTH_ALL = "Show all {n}"
YEAR_ALL = "Show all"
FILTER_CHIP = "{name} \u00b7 {n} photos"

# ---------- about ----------
ABOUT_TITLE = "About this demo"
ABOUT_TEXT = ("A research prototype for finding photos you only half-remember. "
              "The library holds 3,252 freely licensed photos with synthetic dates, "
              "places and people, so nothing here is a real person's library.")
HOW_TITLE = "How Ask Photos works"
HOW_POINTS = (
    "Describe the photo in a sentence \u2014 places, times, what you remember.",
    "Likely matches appear immediately, grouped by date.",
    "Answer a couple of quick questions, or browse by date, until it shows up.",
)
PROVIDER_LINE = "Text understanding: {provider}"
LICENSE_NOTE = ("Photos are freely licensed (CC0 / CC BY / CC BY-SA / public domain). "
                "Credits in ATTRIBUTION.md.")

# ---------- errors ----------
ERROR_GENERIC = "Something went wrong. Please try again."
BTN_TRY_AGAIN = "Try again"
ERROR_FATAL = "Something went wrong in the demo. Please press Start over or reload."

# ---------- test mode (contract-locked) ----------
TM_JOIN = "Join the study"
TM_SUB = "2 practice + 8 tasks \u00b7 about 30 minutes"
TM_CODE_LABEL = "Your participant code (e.g. P1)"
TM_START = "Start session"
TM_BAD_CODE = "Please enter a code like P1, P2 \u2026 P8."
TM_TASK = "Task {id}"
TM_PRACTICE_TAG = "practice (not counted)"
TM_TASK_TAG = "task {n} of 8"
TM_MODE_TAG = "mode: {mode}"
TM_LIMIT = "3:00 \u00b7 no feedback until the end."
TM_LIMIT_PRACTICE = "1:00 \u00b7 no feedback until the end."
TM_START_TASK = "Start task"
TM_GIVE_UP = "I give up"
TM_TIME_UP = "Time's up \u2014 let's move on."
TM_MEMORY_CARD = "Your memory"
TM_MEMORY_SUB = "Start from the task text, or add what you recall."
TM_MEMORY_PH = "Your memory of the photo (start from the card if you like)"
TM_CLASSIC_PH = "a caf\u00e9 in Goa, daytime, coffee"
TM_CONFIRM_TITLE = "Is this the photo?"
TM_CONFIRM_SUB = "Your pick \u2014 say yes if it's right."
TM_KEEP_LOOKING = "Hmm, keep looking."
TM_NOTED = "Noted \u2014 thanks for trying. In free play there's no single right answer."
TM_FINISHED = "Task {id} finished"
TM_CONF_Q = "How sure are you that you picked the right photo? (1\u20135)"
TM_EASE_Q = "How easy was this task? (1\u20137)"
TM_CONTINUE = "Continue"
TM_COMPLETE = "Session complete"
TM_COMPLETE_TXT = "Session complete \u2014 thank you!"
TM_DOWNLOAD = "Download my session log"
TM_ADMIN = "Admin"
TM_ADMIN_DL = "Download all events (events.jsonl)"
TM_ADMIN_FILE = "Download events.jsonl"
TM_ADMIN_NOTE = "Admin view \u2014 normal visitors do not see this."

ASK = "Ask"
GROUP_PHOTOS = "Photos"
GROUP_PHOTOS_SUB = "closest matches"
WHICH_CLOSER = "Which looks closer to what you remember?"
NEITHER = "Neither"
PAIR_LEFT = "Left is closer"
PAIR_RIGHT = "Right is closer"
DETAILS = "Details"
SHARE = "Share"
Q_COLOR = "Which color stands out?"
STUDY_CHIP = "Research session"
OPEN_PHOTO = "Open photo from {d}"
THIS_IS_IT = "This is it \u2714"
