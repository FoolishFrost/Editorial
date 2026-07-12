"""editorial_export.py — Export compilers for RTF and Tagged Text formats."""

import re
from spacy.lang.en.stop_words import STOP_WORDS

from editorial_config import (
    EDITOR_MODE_EMOTION,
    EDITOR_MODE_ECHO,
    EDITOR_MODE_DTAG,
    EDITOR_MODE_PACING,
    EDITOR_MODE_CLICHE,
    EDITOR_MODE_REDUNDANCY,
    EDITOR_MODE_PASSIVE,
    EDITOR_MODE_WEAK,
    EDITOR_MODE_PUNCT,
    EDITOR_MODE_FILTER,
    EDITOR_MODE_ARCH,
)

from filter_analyzer import (
    analyze_dialogue_mechanics,
    analyze_dialogue_tags,
    analyze_emotion_words,
    analyze_filter_words,
    analyze_sentence_pacing,
    analyze_weak_modifiers,
)


def collect_export_ranges(
    app,
    mode: str,
    text: str,
    active_pov: list[str],
    pov_names: set[str] | None = None,
) -> list[tuple[int, int, str]]:
    if mode == EDITOR_MODE_EMOTION:
        if not app._emotion_update_needed and app._emotion_hits:
            return sorted([(ws, we, "emotion") for ws, we in app._emotion_hits], key=lambda x: x[0])
        return sorted(
            [(ws, we, "emotion") for ws, we, _cls in analyze_emotion_words(text)],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_ECHO:
        if not app._echo_update_needed and app._echo_hits:
            return sorted([(ws, we, "echo") for ws, we in app._echo_hits], key=lambda x: x[0])
        from mode_echo_radar import analyze_echo_radar
        result = analyze_echo_radar(text, app._echo_focus_window_words)
        return sorted(
            [(ws, we, "echo") for ws, we in result["ranges"]],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_DTAG:
        if not app._dialogue_tag_update_needed and app._dialogue_tag_hits:
            return sorted([(ws, we, "dialogue_tag") for ws, we in app._dialogue_tag_hits], key=lambda x: x[0])
        return sorted(
            [(ws, we, "dialogue_tag") for ws, we, _cls in analyze_dialogue_tags(text)],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_PACING:
        ranges: list[tuple[int, int, str]] = []
        for ws, we, heat, _wc in analyze_sentence_pacing(
            text,
            short_max_words=app._pacing_short_words,
            average_words=app._pacing_average_words,
            long_min_words=app._pacing_long_words,
        ):
            ranges.append((ws, we, app._pacing_tag_from_heat(heat)))
        return sorted(ranges, key=lambda x: x[0])
    if mode == EDITOR_MODE_CLICHE:
        if not getattr(app, "_cliche_update_needed", False) and getattr(app, "_cliche_hits", None):
            return sorted([(ws, we, "cliche_hit") for ws, we in app._cliche_hits], key=lambda x: x[0])
        from filter_analyzer import analyze_cliches
        return sorted(
            [(ws, we, "cliche_hit") for ws, we, _cls in analyze_cliches(text)],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_REDUNDANCY:
        if not getattr(app, "_redundancy_update_needed", False) and getattr(app, "_redundancy_hits", None):
            return sorted([(ws, we, "redundancy_hit") for ws, we in app._redundancy_hits], key=lambda x: x[0])
        from filter_analyzer import analyze_redundancies
        return sorted(
            [(ws, we, "redundancy_hit") for ws, we, _cls in analyze_redundancies(text)],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_PASSIVE:
        if not getattr(app, "_passive_voice_update_needed", False) and getattr(app, "_passive_voice_hits", None):
            return sorted([(ws, we, "passive_voice_hit") for ws, we in app._passive_voice_hits], key=lambda x: x[0])
        from filter_analyzer import analyze_passive_voice
        return sorted(
            [(ws, we, "passive_voice_hit") for ws, we, _cls in analyze_passive_voice(text)],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_WEAK:
        if not app._weak_update_needed and app._weak_mod_hits:
            return sorted(
                [(ws, we, "orange") for ws, we in app._weak_mod_hits],
                key=lambda x: x[0],
            )
        hits_raw = analyze_weak_modifiers(text)
        return sorted(
            [(ws, we, "orange") for ws, we, _cls in hits_raw],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_PUNCT:
        ranges = []
        if not app._punct_update_needed and any(app._punct_hits.values()):
            for cls, hits in app._punct_hits.items():
                for ws, we in hits:
                    ranges.append((ws, we, cls))
            return sorted(ranges, key=lambda x: x[0])
        for ws, we, cls in analyze_dialogue_mechanics(text):
            ranges.append((ws, we, cls))
        return sorted(ranges, key=lambda x: x[0])
    if mode == EDITOR_MODE_FILTER:
        if not app._filter_update_needed and any(app._filter_hits.values()):
            ranges = []
            for level in ("red", "purple"):
                for ws, we in app._filter_hits.get(level, []):
                    ranges.append((ws, we, level))
            return sorted(ranges, key=lambda x: x[0])
        hits_raw = analyze_filter_words(
            text,
            pov_character_names=pov_names,
            active_pov_pronouns=active_pov,
        )
        return sorted(
            [(ws, we, "red" if cls == "yellow" else cls) for ws, we, cls in hits_raw],
            key=lambda x: x[0],
        )
    if mode == EDITOR_MODE_ARCH:
        if not getattr(app, "_arch_update_needed", False) and getattr(app, "_arch_hits", None):
            return sorted(app._arch_hits, key=lambda x: x[0])
        if getattr(app, "_arch_ignore_dialogue_var", None) and app._arch_ignore_dialogue_var.get():
            text = app._mask_dialogue_text(text)
        from filter_analyzer import analyze_sentence_architecture
        return sorted(analyze_sentence_architecture(text), key=lambda x: x[0])
    return []


def build_tagged_export(
    text: str,
    ranges: list[tuple[int, int, str]],
    label_map: dict[str, str] | None = None,
) -> str:
    if not ranges:
        return text

    out: list[str] = []
    pos = 0

    for start, end, level in ranges:
        if start < pos:
            continue
        out.append(text[pos:start])
        word = text[start:end]
        if label_map and level in label_map:
            out.append(f"[{label_map[level]}:{word}]")
        else:
            out.append(f"[{word}]")
        pos = end

    out.append(text[pos:])
    return "".join(out)


def rtf_escape(s: str) -> str:
    s = s.replace("\\", r"\\").replace("{", r"\}").replace("}", r"\}")
    return s.replace("\n", r"\par " + "\n")


def build_rtf_export(text: str, ranges: list[tuple[int, int, str]]) -> str:
    level_colors: dict[str, tuple[int, int]] = {
        "red":      (1, 2),   # filter words:     RED_FG on RED_BG
        "orange":   (3, 4),   # weak modifiers:   ORANGE_FG on ORANGE_BG
        "quote":    (5, 6),   # quote issues:     PURPLE_FG on PURPLE_BG
        "dash":     (7, 8),   # dashes:           BLUE_FG on BLUE_BG
        "ellipsis": (9, 10),  # ellipsis:         WHITE_FG on WHITE_BG
        "loud":     (1, 2),   # loud punctuation: RED_FG on RED_BG
        "purple":   (5, 6),   # legacy quote:     PURPLE_FG on PURPLE_BG
        "emotion":  (1, 2),   # emotion words:    RED_FG on RED_BG
        "echo":     (7, 8),   # echo radar:       BLUE_FG on BLUE_BG
        "dialogue_tag": (3, 4),
        "typography": (7, 8), # typography scan:  BLUE_FG on BLUE_BG
        "pacing_cool_3": (7, 8),
        "pacing_cool_2": (7, 8),
        "pacing_cool_1": (7, 8),
        "pacing_neutral": (11, 12),
        "pacing_warm_1": (3, 4),
        "pacing_warm_2": (3, 4),
        "pacing_hot": (1, 2),
        "cliche_hit": (13, 14),       # #80cbc4 on #004d40
        "redundancy_hit": (15, 16),   # #ffee58 on #4d4d00
        "passive_voice_hit": (17, 18),# #f06292 on #4a0024
        # Arch: Normal tags
        "arch_subject_first":          (19, 20),   # #a8c8f8 on #1e2d3e
        "arch_participial_launch":     (21, 22),   # #f9d87a on #382d10
        "arch_contextual_lead":        (23, 24),   # #c4a8f8 on #291e3b
        "arch_echoing_hinge":          (25, 26),   # #f4a07a on #3c1e10
        "arch_simultaneous_setup":     (27, 28),   # #a6e3a1 on #1a2e1e
        "arch_fragment":               (29, 30),   # #8a8aaa on #20202c
        # Arch: Stacked tags (with border/intensified colors)
        "arch_subject_first_stacked":          (31, 32),   # #c0dbff on #2d4460
        "arch_participial_launch_stacked":     (33, 34),   # #ffe6a3 on #544318
        "arch_contextual_lead_stacked":        (35, 36),   # #dbccff on #3f2e5a
        "arch_echoing_hinge_stacked":          (37, 38),   # #ffc0a3 on #5a2d18
        "arch_simultaneous_setup_stacked":     (39, 40),   # #c2ffd2 on #284a32
        "arch_fragment_stacked":               (41, 42),   # #b4b4d0 on #303042
    }

    chunks: list[str] = []
    pos = 0
    for start, end, level in ranges:
        if start < pos:
            continue
        if start > pos:
            chunks.append(rtf_escape(text[pos:start]))
        word = rtf_escape(text[start:end])
        cf, highlight = level_colors.get(level, (1, 2))
        underline = level in {"quote", "dash", "ellipsis", "loud", "echo", "typography", "dialogue_tag"}
        is_arch_stacked = False
        prefix = r"{\cf" + str(cf) + r"\highlight" + str(highlight) + " "
        if underline or is_arch_stacked:
            prefix += r"\ul "
        suffix = r"\ul0\highlight0\cf0 }" if (underline or is_arch_stacked) else r"\highlight0\cf0 }"
        chunks.append(prefix + word + suffix)
        pos = end
    chunks.append(rtf_escape(text[pos:]))

    color_table = (
        r"{\colortbl ;"
        r"\red243\green139\blue168;"   #  1 RED_FG   #f38ba8
        r"\red61\green21\blue32;"      #  2 RED_BG   #3d1520
        r"\red242\green205\blue150;"   #  3 ORANGE_FG #f2cd96
        r"\red74\green51\blue32;"      #  4 ORANGE_BG #4a3320
        r"\red30\green30\blue46;"      #  5 PURPLE_FG #1e1e2e
        r"\red249\green226\blue175;"   #  6 PURPLE_BG #f9e2af
        r"\red137\green180\blue250;"   #  7 BLUE_FG  #89b4fa
        r"\red31\green43\blue64;"      #  8 BLUE_BG  #1f2b40
        r"\red245\green245\blue245;"   #  9 WHITE_FG #f5f5f5
        r"\red58\green58\blue58;"      # 10 WHITE_BG #3a3a3a
        r"\red166\green227\blue161;"   # 11 GREEN_FG #a6e3a1
        r"\red26\green46\blue30;"      # 12 GREEN_BG #1a2e1e
        r"\red128\green203\blue196;"   # 13 Cliche FG #80cbc4
        r"\red0\green77\blue64;"       # 14 Cliche BG #004d40
        r"\red255\green238\blue88;"    # 15 Redundancy FG #ffee58
        r"\red77\green77\blue0;"       # 16 Redundancy BG #4d4d00
        r"\red240\green98\blue146;"    # 17 Passive FG #f06292
        r"\red74\green0\blue36;"       # 18 Passive BG #4a0024
        r"\red198\green224\blue255;"   # 19 Arch Subject First FG  #c6e0ff
        r"\red37\green58\blue82;"      # 20 Arch Subject First BG  #253a52
        r"\red255\green235\blue175;"   # 21 Arch Participial Launch FG #ffebaf
        r"\red79\green62\blue26;"      # 22 Arch Participial Launch BG #4f3e1a
        r"\red227\green209\blue255;"   # 23 Arch Contextual Lead FG  #e3d1ff
        r"\red60\green42\blue87;"      # 24 Arch Contextual Lead BG  #3c2a57
        r"\red255\green212\blue192;"   # 25 Arch Echoing Hinge FG #ffd4c0
        r"\red84\green40\blue23;"      # 26 Arch Echoing Hinge BG #542817
        r"\red211\green255\blue217;"   # 27 Arch Simultaneous Setup FG #d3ffd9
        r"\red35\green66\blue42;"      # 28 Arch Simultaneous Setup BG #23422a
        r"\red192\green192\blue216;"   # 29 Arch Fragment FG #c0c0d8
        r"\red48\green48\blue64;"      # 30 Arch Fragment BG #303040
        r"\red230\green242\blue255;"   # 31 Arch Subject First Stacked FG #e6f2ff
        r"\red53\green83\blue117;"     # 32 Arch Subject First Stacked BG #355375
        r"\red255\green243\blue209;"   # 33 Arch Participial Launch Stacked FG #fff3d1
        r"\red110\green86\blue36;"     # 34 Arch Participial Launch Stacked BG #6e5624
        r"\red240\green230\blue255;"   # 35 Arch Contextual Lead Stacked FG #f0e6ff
        r"\red85\green60\blue122;"     # 36 Arch Contextual Lead Stacked BG #553c7a
        r"\red255\green231\blue219;"   # 37 Arch Echoing Hinge Stacked FG #ffe7db
        r"\red117\green56\blue32;"     # 38 Arch Echoing Hinge Stacked BG #753820
        r"\red236\green255\blue239;"   # 39 Arch Simultaneous Setup Stacked FG #ecffef
        r"\red50\green97\blue61;"      # 40 Arch Simultaneous Setup Stacked BG #32613d
        r"\red224\green224\blue240;"   # 41 Arch Fragment Stacked FG #e0e0f0
        r"\red72\green72\blue96;"      # 42 Arch Fragment Stacked BG #484860
        r"}"
    )
    header = (
        r"{\rtf1\ansi\deff0"
        r"{\fonttbl{\f0 Consolas;}}"
        + color_table +
        r"\viewkind4\uc1\pard\f0\fs22 "
    )
    return header + "".join(chunks) + r"}"
