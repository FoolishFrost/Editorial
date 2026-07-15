"""editorial_config.py — Static configurations, parameters, and style schemes."""

APP_NAME = "Editorial"
APP_VERSION = "1.5.0"
COMPANY_NAME = "Foolish Designs"
CREATOR_NAME = "John Bowden"
SUPPORT_EMAIL = "johnbowden@foolishdesigns.com"
GITHUB_REPO = "FoolishFrost/Editorial"
WIKI_URL = "https://github.com/FoolishFrost/Editorial/wiki"
RELEASES_URL = "https://github.com/FoolishFrost/Editorial/releases"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ---------------------------------------------------------------------------
# Colour palette  (Catppuccin Mocha-inspired dark theme)
# ---------------------------------------------------------------------------
BG          = "#1e1e2e"   # base background
BG_SURFACE  = "#181825"   # toolbar / panel background
BG_OVERLAY  = "#313244"   # hover / selection overlay
TEXT        = "#cdd6f4"   # primary text
TEXT_SUBTLE = "#6c7086"   # muted labels
ACCENT      = "#89b4fa"   # blue accent (cursor, scrollbar)

# Filter highlight colours
RED_FG    = "#f38ba8"
RED_BG    = "#3d1520"
GREEN_FG  = "#a6e3a1"
GREEN_BG  = "#1a2e1e"
PURPLE_FG = "#1e1e2e"
PURPLE_BG = "#f9e2af"
ORANGE_FG = "#f2cd96"
ORANGE_BG = "#4a3320"
BLUE_FG   = "#89b4fa"
BLUE_BG   = "#1f2b40"
WHITE_FG  = "#f5f5f5"
WHITE_BG  = "#3a3a3a"
FIND_BG   = "#45475a"

PACING_SHORT_WORDS = 3
PACING_AVERAGE_WORDS = 12
PACING_LONG_WORDS = 19

PACING_TAG_STYLES: tuple[tuple[str, str, str], ...] = (
    ("pacing_cool_3", "#eaf5ff", "#14395f"),
    ("pacing_cool_2", "#e3f6ff", "#1b4a73"),
    ("pacing_cool_1", "#def7ff", "#255e83"),
    ("pacing_neutral", "#deffe5", "#21482d"),
    ("pacing_warm_1", "#fff1c9", "#61501f"),
    ("pacing_warm_2", "#ffe0c6", "#6d341d"),
    ("pacing_hot", "#ffe0e0", "#652126"),
)

PACING_EXPORT_LABELS = {
    "pacing_cool_3": "VERY SHORT",
    "pacing_cool_2": "SHORT",
    "pacing_cool_1": "BRISK",
    "pacing_neutral": "BALANCED",
    "pacing_warm_1": "STRETCHED",
    "pacing_warm_2": "LONG",
    "pacing_hot": "VERY LONG",
}

POV_PRONOUN_MAP: dict[str, list[str]] = {
    "First Person (I/We)": ["i", "we", "me", "us"],
    "Third Person Male (He)": ["he", "him"],
    "Third Person Female (She)": ["she", "her"],
    "Third Person Plural (They)": ["they", "them"],
    "All Pronouns (Broad Scan)": ["i", "we", "he", "she", "they", "me", "us", "him", "her", "them"],
}

EDITOR_MODE_OFF = "off"
EDITOR_MODE_FILTER = "filter_words"
EDITOR_MODE_WEAK = "weak_modifiers"
EDITOR_MODE_PUNCT = "dialogue_punctuation"
EDITOR_MODE_DTAG = "dialogue_tags"
EDITOR_MODE_EMOTION = "emotion_catcher"
EDITOR_MODE_ECHO = "echo_radar"
EDITOR_MODE_PACING = "rhythm_pacing"
EDITOR_MODE_CLICHE = "cliches"
EDITOR_MODE_REDUNDANCY = "redundancies"
EDITOR_MODE_PASSIVE = "passive_voice"
EDITOR_MODE_ARCH = "sentence_architecture"
EDITOR_MODE_SPELL = "spelling_checker"

EDITOR_MODES: list[tuple[str, str]] = [
    ("Editor Off", EDITOR_MODE_OFF),
    ("Filter Words", EDITOR_MODE_FILTER),
    ("Weak Modifiers", EDITOR_MODE_WEAK),
    ("Punctuation", EDITOR_MODE_PUNCT),
    ("Dialogue Tags", EDITOR_MODE_DTAG),
    ("Emotion Catcher", EDITOR_MODE_EMOTION),
    ("Proximity Echo Radar", EDITOR_MODE_ECHO),
    ("Rhythm & Pacing", EDITOR_MODE_PACING),
    ("Cliches", EDITOR_MODE_CLICHE),
    ("Redundancies", EDITOR_MODE_REDUNDANCY),
    ("Passive Voice", EDITOR_MODE_PASSIVE),
    ("Sentence Architecture", EDITOR_MODE_ARCH),
    ("Spelling Checker", EDITOR_MODE_SPELL),
]

ARCH_TAG_STYLES: tuple[tuple[str, str, str, bool], ...] = (
    # Normal tags
    ("arch_subject_first",          "#253a52", "#c6e0ff", False),  # steel blue
    ("arch_participial_launch",     "#4f3e1a", "#ffebaf", False),  # warm gold
    ("arch_contextual_lead",        "#3c2a57", "#e3d1ff", False),  # soft amethyst
    ("arch_echoing_hinge",          "#542817", "#ffd4c0", False),  # terracotta
    ("arch_simultaneous_setup",     "#23422a", "#d3ffd9", False),  # sage green
    ("arch_fragment",               "#303040", "#c0c0d8", False),  # slate grey

    # Stacked tags (styled identically to normal tags)
    ("arch_subject_first_stacked",          "#253a52", "#c6e0ff", False),
    ("arch_participial_launch_stacked",     "#4f3e1a", "#ffebaf", False),
    ("arch_contextual_lead_stacked",        "#3c2a57", "#e3d1ff", False),
    ("arch_echoing_hinge_stacked",          "#542817", "#ffd4c0", False),
    ("arch_simultaneous_setup_stacked",     "#23422a", "#d3ffd9", False),
    ("arch_fragment_stacked",               "#303040", "#c0c0d8", False),
)

ARCH_EXPORT_LABELS: dict[str, str] = {
    "arch_subject_first":          "SUBJECT_FIRST",
    "arch_subject_first_stacked":  "SUBJECT_FIRST_STACKED",
    "arch_participial_launch":     "PARTICIPIAL_LAUNCH",
    "arch_participial_launch_stacked": "PARTICIPIAL_LAUNCH_STACKED",
    "arch_contextual_lead":        "CONTEXTUAL_LEAD",
    "arch_contextual_lead_stacked": "CONTEXTUAL_LEAD_STACKED",
    "arch_echoing_hinge":          "ECHOING_HINGE",
    "arch_echoing_hinge_stacked":  "ECHOING_HINGE_STACKED",
    "arch_simultaneous_setup":     "SIMULTANEOUS_SETUP",
    "arch_simultaneous_setup_stacked": "SIMULTANEOUS_SETUP_STACKED",
    "arch_fragment":               "FRAGMENT",
    "arch_fragment_stacked":       "FRAGMENT_STACKED",
}

ARCH_FRIENDLY_LABELS: dict[str, str] = {
    "arch_subject_first": "Subject-First",
    "arch_participial_launch": "Participial Launch",
    "arch_contextual_lead": "Contextual Lead",
    "arch_echoing_hinge": "Echoing Hinge",
    "arch_simultaneous_setup": "Simultaneous",
    "arch_fragment": "Fragment",
}
