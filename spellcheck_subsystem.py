import os
import json
import re
import gzip
from spellchecker import SpellChecker
from analysis_utils import _get_base_dir

try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False


def _write_spellchecker_dictionary_file(payload: bytes, destination: str) -> str:
    destination_path = os.path.abspath(destination)
    directory = os.path.dirname(destination_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination_path, "wb") as fh:
        fh.write(gzip.decompress(payload))
    return destination_path


def _extract_spellcheck_tokens(content: str) -> list[tuple[str, tuple[int, int]]]:
    tokens: list[tuple[str, tuple[int, int]]] = []
    for match in re.finditer(r"[A-Za-z]+(?:['\u2019][A-Za-z]+)?", content):
        word = match.group(0)
        normalized_word = word.replace("\u2019", "'")
        if "'" in normalized_word:
            continue
        tokens.append((word, match.span()))
    return tokens


class SpellcheckSubsystem:
    """Subsystem class that owns the SpellChecker engine and dictionary files."""

    def __init__(self, custom_dict_path: str, local_dict_path: str | None = None) -> None:
        self.local_dict_path = local_dict_path
        if local_dict_path and os.path.exists(local_dict_path):
            try:
                self.spellchecker = SpellChecker(language=None, local_dictionary=local_dict_path)
            except Exception:
                try:
                    self.spellchecker = SpellChecker(language="en")
                except Exception:
                    self.spellchecker = SpellChecker()
        else:
            try:
                self.spellchecker = SpellChecker(language="en")
            except Exception:
                self.spellchecker = SpellChecker()

        self.custom_dict_path = os.path.abspath(custom_dict_path)
        self.custom_dict_words: set[str] = set()
        self.ignored_words: set[str] = set()
        self.ignored_confusions: set[tuple[int, int]] = set()
        self.load_custom_dictionary()
        self.load_word_confusions()
        self._load_spacy()

    def reinit_spellchecker(self) -> None:
        """Re-initialize the spellchecker instance to discard removed words."""
        if self.local_dict_path and os.path.exists(self.local_dict_path):
            try:
                self.spellchecker = SpellChecker(language=None, local_dictionary=self.local_dict_path)
            except Exception:
                try:
                    self.spellchecker = SpellChecker(language="en")
                except Exception:
                    self.spellchecker = SpellChecker()
        else:
            try:
                self.spellchecker = SpellChecker(language="en")
            except Exception:
                self.spellchecker = SpellChecker()
        self.load_custom_dictionary()


    def load_custom_dictionary(self) -> None:
        """Load the user's custom dictionary words from file."""
        try:
            if os.path.exists(self.custom_dict_path):
                with open(self.custom_dict_path, "r", encoding="utf-8") as fh:
                    words = json.load(fh)
                    if isinstance(words, list):
                        self.custom_dict_words = set(words)
                        self.spellchecker.word_frequency.load_words(words)
        except Exception:
            pass

    def save_custom_dictionary(self) -> None:
        """Save the custom dictionary words to file."""
        try:
            directory = os.path.dirname(self.custom_dict_path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.custom_dict_path, "w", encoding="utf-8") as fh:
                json.dump(list(self.custom_dict_words), fh)
        except Exception:
            pass

    def add_to_dictionary(self, word: str) -> None:
        """Add a word to the custom dictionary (case-insensitive) and trigger save."""
        word_lower = word.lower()
        self.custom_dict_words.add(word_lower)
        self.spellchecker.word_frequency.load_words([word_lower])
        self.save_custom_dictionary()

    def ignore_word(self, word: str) -> None:
        """Ignore a spelling error for the current session (case-insensitive)."""
        self.ignored_words.add(word.lower())

    def get_candidates(self, word: str) -> set[str] | None:
        """Retrieve potential spelling corrections for a given word."""
        return self.spellchecker.candidates(word)

    def check_spelling(self, content: str, pov_names: set[str] | None = None) -> list[tuple[int, int]]:
        """
        Run spelling check on content, returning lists of spans for misspelled words.
        Optimized by checking only unique lowercase words and filtering out ignored terms.
        """
        if not content.strip():
            return []

        tokens = _extract_spellcheck_tokens(content)
        if not tokens:
            return []

        words = [word for word, _ in tokens]
        spans = [span for _, span in tokens]

        # Lowercase and deduplicate spelling candidates to minimize spellchecker lookups
        pov_names_lower = {name.lower() for name in pov_names} if pov_names else set()
        unique_words = {
            w.lower() for w in words
            if w.lower() not in self.ignored_words and w.lower() not in pov_names_lower
        }

        unknown_unique = self.spellchecker.unknown(list(unique_words))

        misspelled = []
        for i, word in enumerate(words):
            if word.lower() in unknown_unique:
                misspelled.append(spans[i])

        return misspelled

    # ------------------------------------------------------------------
    # spaCy-powered word confusion detection
    # ------------------------------------------------------------------

    def _load_spacy(self) -> None:
        """Load the spaCy model used for POS-based word confusion detection."""
        self.nlp = None
        if not _SPACY_AVAILABLE:
            return
        for model_name in ("en_core_web_sm", "en_core_web_md", "en_core_web_lg"):
            try:
                self.nlp = spacy.load(model_name, disable=["ner", "lemmatizer"])
                break
            except Exception:
                continue

    @staticmethod
    def _next_token(doc, index: int):
        """Return the next non-space, non-punct token after *index* in the same sentence, or None."""
        current_token = doc[index]
        for j in range(index + 1, len(doc)):
            t = doc[j]
            if t.sent != current_token.sent:
                break
            if not t.is_space and not t.is_punct:
                return t
        return None

    @staticmethod
    def _prev_token(doc, index: int):
        """Return the previous non-space, non-punct token before *index* in the same sentence, or None."""
        current_token = doc[index]
        for j in range(index - 1, -1, -1):
            t = doc[j]
            if t.sent != current_token.sent:
                break
            if not t.is_space and not t.is_punct:
                return t
        return None

    def _flag(self, token, suggest: str, explanation: str) -> tuple[int, int, str, str]:
        return (token.idx, token.idx + len(token.text), suggest, explanation)

    def check_word_confusion(self, content: str) -> list[tuple[int, int, str, str]]:
        """
        Use spaCy POS tagging and regex-based patterns to detect word confusions with accuracy.
        Returns list of (start, end, suggestion, explanation) tuples.
        """
        if not content.strip():
            return []

        results: list[tuple[int, int, str, str]] = []

        # 1. Regex-based checks
        if hasattr(self, "confusion_rules") and self.confusion_rules:
            for rule in self.confusion_rules:
                for match in rule["re"].finditer(content):
                    start, end = match.span()
                    matched_text = match.group(0)
                    trigger = rule["trigger"]
                    trigger_match = re.search(r"\b" + re.escape(trigger) + r"\b", matched_text, re.IGNORECASE)
                    if trigger_match:
                        t_start = start + trigger_match.start()
                        t_end = start + trigger_match.end()
                    else:
                        t_start, t_end = start, end
                    
                    if (t_start, t_end) in self.ignored_confusions:
                        continue
                    
                    results.append((t_start, t_end, rule["suggest"], rule["explanation"]))

        # 2. spaCy-based checks
        if self.nlp is not None:
            try:
                doc = self.nlp(content)
                for i, token in enumerate(doc):
                    span = (token.idx, token.idx + len(token.text))
                    if span in self.ignored_confusions:
                        continue

                    word_lower = token.text.lower()
                    nxt = self._next_token(doc, i)
                    prv = self._prev_token(doc, i)

                    # ----------------------------------------------------------------
                    # their / there / they're
                    # ----------------------------------------------------------------
                    if word_lower == "their":
                        if nxt is not None:
                            # "their" before a form of 'be' or existential context
                            # → "There was/is/are/were a …"
                            if nxt.lemma_ == "be" and nxt.pos_ in ("AUX", "VERB"):
                                results.append(self._flag(
                                    token, "There",
                                    "'There' introduces existential clauses ('There was …'); "
                                    "'their' is possessive."
                                ))
                            # "their" before a present/past participle where no noun follows
                            # (e.g. "their going", "their running") → "they're"
                            elif nxt.tag_ == "VBG" and nxt.dep_ not in ("pcomp",):
                                results.append(self._flag(
                                    token, "they're",
                                    "'they're' = 'they are'; 'their' is possessive."
                                ))

                    elif word_lower == "there":
                        # Detect "there" used as a possessive determiner (should be "their").
                        # Legitimate existential "there" carries dep="expl" in spaCy's parse.
                        # Misused "there" (e.g. "there coats") will have dep="advmod" or similar.
                        if nxt is not None and nxt.pos_ in ("NOUN", "PROPN"):
                            is_existential = (
                                token.dep_ == "expl"
                                or any(
                                    t.pos_ in ("VERB", "AUX") and t.dep_ == "ROOT"
                                    for t in doc[i:min(len(doc), i + 4)]
                                )
                            )
                            if not is_existential:
                                results.append(self._flag(
                                    token, "their",
                                    "'their' is possessive; 'there' indicates a location."
                                ))

                    # ----------------------------------------------------------------
                    # its / it's
                    # spaCy tokenises "it's" → [it]['][s], so we only see "its" here.
                    # ----------------------------------------------------------------
                    elif word_lower == "its":
                        if nxt is not None:
                            # Standard case: "its" before a finite verb/aux ("its was", "its is")
                            if nxt.pos_ in ("VERB", "AUX") and nxt.tag_ not in ("VBG",):
                                results.append(self._flag(
                                    token, "it's",
                                    "'it's' = 'it is / it has'; 'its' is possessive."
                                ))
                            # Edge case: spaCy sometimes reads "Its raining" as a noun phrase
                            # tagging "raining" as NN.  Catch: "its" dep=poss, head tagged NN.
                            elif (token.dep_ == "poss"
                                  and token.head.tag_ == "NN"
                                  and token.head.text.endswith("ing")):
                                results.append(self._flag(
                                    token, "it's",
                                    "'it's' = 'it is / it has'; 'its' is possessive."
                                ))

                    # ----------------------------------------------------------------
                    # your / you're
                    # ----------------------------------------------------------------
                    elif word_lower == "your":
                        # spaCy tags "Your going" as PRP$/nsubj + VBG/ROOT.
                        # Include VBG here (unlike the its rule) because "your going"
                        # is unambiguously a contraction error.
                        if (nxt is not None
                                and nxt.pos_ in ("VERB", "AUX")):
                            results.append(self._flag(
                                token, "you're",
                                "'you're' = 'you are'; 'your' is possessive."
                            ))

                    # ----------------------------------------------------------------
                    # then / than  (comparative context)
                    # ----------------------------------------------------------------
                    elif word_lower == "then":
                        # Preceded by a comparative adjective or adverb (JJR / RBR)
                        if prv is not None and prv.tag_ in ("JJR", "RBR"):
                            results.append(self._flag(
                                token, "than",
                                "Use 'than' for comparisons ('better than'); "
                                "'then' indicates time or sequence."
                            ))

                    # ----------------------------------------------------------------
                    # loose / lose
                    # ----------------------------------------------------------------
                    elif word_lower == "loose":
                        # spaCy tags "loose" as VERB when used incorrectly as one
                        if token.pos_ == "VERB":
                            results.append(self._flag(
                                token, "lose",
                                "'lose' is a verb (to misplace/fail); "
                                "'loose' is an adjective (not tight)."
                            ))

                    # ----------------------------------------------------------------
                    # passed / past  (directional preposition)
                    # ----------------------------------------------------------------
                    elif word_lower == "passed":
                        # Preceded by a motion verb → directional "past"
                        # Use .text.lower() because lemmatizer may be disabled.
                        _motion_verbs = {
                            "walked", "ran", "drove", "flew", "sprinted",
                            "hurried", "went", "came", "rushed", "marched",
                            "strode", "strolled", "jogged", "rode", "sailed",
                            "walk", "run", "drive", "fly", "sprint",
                            "hurry", "go", "come", "rush", "march",
                            "stride", "stroll", "jog", "ride", "sail",
                        }
                        if prv is not None and prv.text.lower() in _motion_verbs:
                            results.append(self._flag(
                                token, "past",
                                "'past' is a preposition of direction ('walked past me'); "
                                "'passed' is the past tense of 'to pass'."
                            ))
            except Exception:
                pass

        # Deduplicate / resolve overlapping spans (keep earliest)
        results.sort(key=lambda x: x[0])
        resolved: list[tuple[int, int, str, str]] = []
        last_end = -1
        for item in results:
            if item[0] >= last_end:
                resolved.append(item)
                last_end = item[1]
        return resolved

    def load_word_confusions(self) -> None:
        self.confusion_rules = []
        path = os.path.join(_get_base_dir(), "word_confusions.json")
        try:
            if not os.path.exists(path):
                default_rules = [
                    {
                        "id": "its_verb",
                        "trigger": "its",
                        "pattern": "\\bits\\s+(is|was|has|had|been|a|an|the|very|not|only)\\b",
                        "suggest": "it's",
                        "explanation": "'it's' is a contraction of 'it is' or 'it has'; 'its' is possessive."
                    },
                    {
                        "id": "its_participle",
                        "trigger": "its",
                        "pattern": "\\bits\\s+[a-z]+ing(?:\\s+(?:at|on|in|to|for|with|by|from|of|about|up|down|out|away|here|there|now|then|again|too|very|so|already|outside|inside|me|you|him|her|us|them|it|a|an|the|not)\\b|(?=\\s*[,.!?;:\\-—\\)]|$))",
                        "suggest": "it's",
                        "explanation": "Usually followed by a participle (e.g., 'it's raining'). Use 'it's'."
                    },
                    {
                        "id": "its_possessive",
                        "trigger": "it's",
                        "pattern": "\\bit's\\s+(own|name|eyes|face|head|body|life|mind|back|hand|hands|feet|foot|leg|legs|arm|arms|tail|wings|wing|voice|sound|light|color|size|shape|weight|length|width|height|depth|age|history|origin|power|strength|weakness|nature|beauty|truth|value|meaning|purpose|effect|cause|result|impact|role|job|work|duty|task|care|love|blood|bone|bones|skin|hair|fur|feather|feathers|teeth|tooth|mouth|nose|ear|ears|heart|brain|soul|spirit|sword|shield|armor|weapon|weapons|tool|tools|device|machine|car|house|room|door|window|wall|roof|floor|garden|tree|flower|plant|animal|dog|cat|bird|fish|prey|predator|victim|target|enemy|friend|allies|ally|partner|leader|member|team|group|class|family|home|land|country|state|city|town|street|road|path|river|lake|sea|ocean|sky|wind|rain|snow|ice|fire|smoke|ash|dust|dirt|stone|rock|sand|metal|gold|silver|iron|wood|paper|glass|plastic|cloth|leather|clothes|food|water|drink|wine|beer|milk|honey|fruit|apple|bread|meat|cheese|egg|eggs|seed|seeds|grain|leaf|leaves|branch|root|roots|trunk|bark|shell|scales|scale|claw|claws|horn|horns|beak|beaks|hoof|hoofs|paw|paws|furry|bloody|bony|cold|warm|hot|dry|wet|soft|hard|rough|smooth|sharp|dull|heavy|light|dark|bright|clean|dirty|new|old|young|mature|fresh|stale|sweet|sour|bitter|salty|loud|quiet|silent|fast|slow|quick|rapid|sudden|gentle|fierce|wild|tame|smart|dumb|wise|foolish|brave|cowardly|weak|strong|sick|healthy|dead|alive|happy|sad|angry|scared|proud|humble|rich|poor|cheap|expensive|free|bound|safe|dangerous|secret|public|private|personal|local|global|national|foreign|strange|weird|odd|normal|usual|unusual|special|common|rare|unique|perfect|imperfect|flawed|correct|incorrect|wrong|right|true|false|real|fake|artificial|natural|organic|inorganic|chemical|physical|mental|emotional|spiritual|moral|immoral|legal|illegal|fair|unfair|just|unjust|good|bad|evil|holy|sinful|sacred|profane|divine|mortal|immortal|human|alien|monster|beast|god|gods|goddess|devil|angel|ghost|phantom|spirit|demon|witch|wizard|mage|priest|king|queen|prince|princess|lord|lady|knight|soldier|guard|warrior|hunter|thief|rogue|assassin|spy|messenger|servant|slave|master|boss|owner|ruler|citizen|subject|peasant|farmer|merchant|trader|craftsman|builder|artist|writer|poet|singer|actor|dancer|musician|doctor|healer|teacher|student|scholar|sage|philosopher|scientist|engineer|inventor|pilot|driver|captain|crew|sailor|pirate|explorer|pioneer|colonist|native|settler|refugee|exile|outlaw|prisoner|hostage|victim|survivor|witness|suspect|criminal|judge|lawyer|police|sheriff|detective|spy|agent|officer|general|major|colonel|captain|lieutenant|sergeant|corporal|private|recruit|veteran)\\b",
                        "suggest": "its",
                        "explanation": "'its' is possessive; 'it's' is a contraction of 'it is' or 'it has'."
                    },
                    {
                        "id": "your_adjective",
                        "trigger": "your",
                        "pattern": "\\byour\\s+(welcome|going|right|correct|sure|late|very|too|so|coming|eating|waiting|doing)\\b",
                        "suggest": "you're",
                        "explanation": "'you're' means 'you are'; 'your' is possessive."
                    },
                    {
                        "id": "theyre_noun",
                        "trigger": "they're",
                        "pattern": "\\bthey're\\s+(car|house|dog|cat|parents|kids|son|daughter|friend|friends|idea|problem|job|book)\\b",
                        "suggest": "their",
                        "explanation": "'their' is possessive; 'they're' is a contraction of 'they are'."
                    },
                    {
                        "id": "their_verb",
                        "trigger": "their",
                        "pattern": "\\btheir\\s+(is|was|are|were|going|coming|doing|having|ready|very|too|so|not|here|there)\\b",
                        "suggest": "they're",
                        "explanation": "'they're' means 'they are'; 'their' is possessive."
                    },
                    {
                        "id": "there_possessive",
                        "trigger": "there",
                        "pattern": "\\bthere\\s+(car|house|dog|cat|parents|kids|son|daughter|friend|friends|idea|problem|job|book)\\b",
                        "suggest": "their",
                        "explanation": "'their' is possessive; 'there' indicates location."
                    },
                    {
                        "id": "then_comparative",
                        "trigger": "then",
                        "pattern": "\\b(more|less|better|worse|bigger|smaller|faster|slower|rather|other|older|younger)\\s+then\\b",
                        "suggest": "than",
                        "explanation": "Use 'than' for comparisons (e.g., 'more than'); 'then' indicates time/sequence."
                    },
                    {
                        "id": "loose_verb",
                        "trigger": "loose",
                        "pattern": "\\b(don't|did|do|will|would|can|could|might|to)\\s+loose\\b",
                        "suggest": "lose",
                        "explanation": "'lose' is a verb (to misplace/fail); 'loose' is an adjective (not tight)."
                    },
                    {
                        "id": "passed_motion",
                        "trigger": "passed",
                        "pattern": "\\b(walked|ran|drove|flew|sprinted|walk|run|drive|fly|sprint|hurried|went|go|came|come)\\s+passed\\b",
                        "suggest": "past",
                        "explanation": "Use 'past' as a preposition of direction (e.g., 'walked past me'); 'passed' is the past tense of 'to pass'."
                    }
                ]
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(default_rules, fh, indent=2)
            
            with open(path, "r", encoding="utf-8") as fh:
                rules = json.load(fh)
                for r in rules:
                    r["re"] = re.compile(r["pattern"], re.IGNORECASE)
                    self.confusion_rules.append(r)
        except Exception:
            pass

    def ignore_confusion(self, start: int, end: int) -> None:
        self.ignored_confusions.add((start, end))
