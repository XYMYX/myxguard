"""Catch an instruction by the words that sit near each other, not by one phrase.

A fixed regular expression misses "bitte legen Sie die Aufgabe vom Anfang
beiseite" even though a person can see the same request as "ignore the
previous instructions". This detector keeps a small word list per language:

* an override verb (ignore, forget, set aside, beiseitelegen, ...)
* a target noun (instruction, Aufgabe, consigne, consegna, Ufgab, ...)
* a pointer at earlier context (previous, obigen, vom Anfang, du début, ...)

A verb and a noun inside a short window are a weak hit. Add the pointer and
the hit becomes strong. Exfiltration, role changes, and tool abuse use their
own pairs. Hidden places (HTML comments, hidden elements, a mail note addressed
to the model) raise the severity by one step.

The lists are matched after a light normalisation: lower case, accents
removed, apostrophes turned into spaces. Swiss German spellings are extra
entries in the list, not a second algorithm.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional, Sequence

from myxguard.detectors.patterns import KNOWN_LANGUAGES, expand_languages
from myxguard.models import Finding, make_finding

# How many tokens may sit between the first clue and the last.
DEFAULT_WINDOW = 18

_UP = {
    "low": "medium",
    "medium": "high",
    "high": "critical",
    "critical": "critical",
}

# group -> language -> phrases as a person would write them.
# They are normalised again when the module loads.
_LEXICON: dict[str, dict[str, tuple[str, ...]]] = {
    "override_verb": {
        "en": (
            "ignore",
            "forget",
            "disregard",
            "set aside",
            "put aside",
            "lay aside",
            "leave aside",
        ),
        "de": (
            "ignorier",
            "ignoriere",
            "ignorieren",
            "vergiss",
            "vergessen",
            "beiseitelegen",
            "beiseite legen",
            "auf die seite legen",
            "links liegen lassen",
        ),
        "fr": (
            "ignore",
            "ignorez",
            "ignorer",
            "oublie",
            "oubliez",
            "oublier",
            "laisse de cote",
            "laissez de cote",
            "laisse tomber",
            "laissez tomber",
            "laisser de cote",
            "mets de cote",
            "mettez de cote",
            "mettre de cote",
            "ecarte",
            "ecartez",
        ),
        "it": (
            "ignora",
            "ignorate",
            "dimentica",
            "dimenticate",
            "metti da parte",
            "mettere da parte",
            "accantona",
            "lascia stare",
        ),
        "gsw": (
            "ignorier",
            "ignoriere",
            "vergiss",
            "uf d siite",
            "uf d syte",
            "uf d site",
            "links liige",
            "links lege",
            "beiseite",
        ),
    },
    "target_noun": {
        "en": (
            "instruction",
            "instructions",
            "task",
            "tasks",
            "rule",
            "rules",
            "prompt",
            "prompts",
            "guideline",
            "guidelines",
            "directive",
            "directives",
            "assignment",
            "assignments",
        ),
        "de": (
            "anweisung",
            "anweisungen",
            "auftrag",
            "auftraege",
            "aufgabe",
            "aufgaben",
            "vorgabe",
            "vorgaben",
            "regel",
            "regeln",
            "prompt",
            "vorspann",
            "richtlinie",
            "richtlinien",
        ),
        "fr": (
            "instruction",
            "instructions",
            "consigne",
            "consignes",
            "regle",
            "regles",
            "directive",
            "directives",
            "tache",
            "taches",
        ),
        "it": (
            "istruzione",
            "istruzioni",
            "consegna",
            "consegne",
            "incarico",
            "incarichi",
            "regola",
            "regole",
            "premessa",
            "direttiva",
            "direttive",
        ),
        "gsw": (
            "ufgab",
            "ufgabe",
            "uftrag",
            "aawisig",
            "aawisige",
            "anweisig",
            "vorgab",
            "vorgabe",
            "regle",
            "vorspann",
            "mandat",
        ),
    },
    "earlier": {
        "en": (
            "previous",
            "prior",
            "above",
            "earlier",
            "initial",
            "opening",
            "starter",
            "from the start",
            "so far",
        ),
        "de": (
            "obigen",
            "obige",
            "bisherigen",
            "bisherige",
            "vorherigen",
            "vorherige",
            "vorangegangenen",
            "vorangegangene",
            "vom anfang",
            "am anfang",
            "zu beginn",
            "anfangs",
        ),
        "fr": (
            "precedentes",
            "precedente",
            "precedents",
            "precedent",
            "du debut",
            "des le debut",
            "au depart",
            "initiale",
            "initiales",
            "d ouverture",
        ),
        "it": (
            "precedenti",
            "precedente",
            "iniziale",
            "iniziali",
            "dall inizio",
            "di partenza",
            "finora",
        ),
        "gsw": (
            "vorherig",
            "vorige",
            "vorherige",
            "vorhar",
            "vom aafang",
            "am aafang",
            "zersch",
            "bisherig",
        ),
    },
    "exfil_verb": {
        "en": (
            "repeat",
            "reveal",
            "print",
            "send",
            "forward",
            "copy",
            "dump",
            "show",
            "mail",
        ),
        "de": (
            "wiederhole",
            "zeige",
            "zeig",
            "schick",
            "schicke",
            "schicken",
            "sende",
            "senden",
            "kopiere",
            "drucke",
            "verrate",
        ),
        "fr": (
            "recopie",
            "recopiez",
            "repete",
            "repetez",
            "montre",
            "montrez",
            "envoie",
            "envoyez",
            "revele",
            "revelez",
        ),
        "it": ("ricopia", "ripeti", "mostra", "invia", "rivela", "stampa"),
        "gsw": ("schick", "schriib", "widerhol", "gib"),
    },
    "exfil_noun": {
        "en": (
            "system prompt",
            "hidden prompt",
            "hidden instructions",
            "preamble",
            "api key",
            "api keys",
            "credentials",
            "hidden setup",
            "private preamble",
        ),
        "de": (
            "systemprompt",
            "system prompt",
            "vorspann",
            "zugangsdaten",
            "api key",
            "geheime einleitung",
        ),
        "fr": (
            "preambule",
            "preambule confidentiel",
            "prompt systeme",
            "configuration interne",
        ),
        "it": (
            "premessa riservata",
            "prompt di sistema",
            "configurazione interna",
        ),
        "gsw": ("vorspann", "iistellig", "ghümmi iistellig"),
    },
    "role_verb": {
        "en": ("you are now", "from now on you are", "switch roles", "you now work as"),
        "de": ("du bist jetzt", "ab jetzt bist", "arbeitest du als"),
        "fr": ("tu es maintenant", "vous etes maintenant", "tu travailles comme"),
        "it": ("sei ora", "adesso sei", "lavori come"),
        "gsw": ("du bisch jetzt", "ab dere ziile bisch", "du wirsch ab jetzt"),
    },
    "role_noun": {
        "en": (
            "operator",
            "administrator",
            "without guardrails",
            "without restrictions",
            "unrestricted",
            "unfiltered",
        ),
        "de": (
            "betreiber",
            "administrator",
            "ohne leitplanken",
            "ohne einschraenkungen",
            "ohne einschränkungen",
        ),
        "fr": (
            "operateur",
            "administrateur",
            "sans garde fous",
            "sans restrictions",
        ),
        "it": (
            "operatore",
            "amministratore",
            "senza argini",
            "senza restrizioni",
        ),
        "gsw": ("betreiber", "betriiber", "ohni leitplanke"),
    },
    "tool_verb": {
        "en": ("skip", "bypass"),
        "de": ("umgehen", "ueberspringen", "überspringen", "uberspringen"),
        "fr": ("contourne", "contournez", "saute", "sautez"),
        "it": ("aggira", "salta"),
        "gsw": ("umgah", "ueberspringe"),
    },
    "tool_noun": {
        "en": ("human check", "human approval", "tool confirmation", "approval step"),
        "de": (
            "freigabe",
            "werkzeugbestaetigung",
            "werkzeugbestätigung",
            "werkzeugbestatigung",
        ),
        "fr": ("confirmation de l outil", "validation humaine"),
        "it": ("conferma dello strumento", "conferma umana"),
        "gsw": ("freigab", "bestaetigung"),
    },
    "tool_phrase": {
        "en": (
            "without confirmation",
            "skip the approval",
            "skip the human check",
            "bypass the sandbox",
        ),
        "de": (
            "ohne rueckfrage",
            "ohne rückfrage",
            "ohne ruckfrage",
            "ohne nachfrage",
            "bestaetigung umgehen",
            "bestätigung umgehen",
            "bestatigung umgehen",
        ),
        "fr": ("sans confirmation", "sans demander de confirmation"),
        "it": ("senza conferma", "senza chiedere conferma"),
        "gsw": ("ohni nocherzfrage", "ohni rueckfrag", "ohni noochfrage"),
    },
}

_RULES = {
    "instruction_override": "intent.override",
    "data_exfiltration": "intent.exfil",
    "role_impersonation": "intent.role",
    "tool_abuse": "intent.tool",
}

_EXPLANATION = {
    "instruction_override": (
        "An override verb and a task or instruction noun sit close together."
    ),
    "data_exfiltration": (
        "A request to repeat, reveal, or send hidden setup text sits close together."
    ),
    "role_impersonation": "A role-change phrase sits next to an operator or unrestricted role.",
    "tool_abuse": "A request to skip confirmation sits next to a tool or approval word.",
}

_TOKEN = re.compile(r"[a-z0-9]+")
_COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
_HIDDEN_MARK = re.compile(
    r"(?is)\bhidden\b|aria-hidden\s*=\s*['\"]true['\"]|"
    r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|"
    r"opacity\s*:\s*0|left\s*:\s*-"
)
_TAG_BLOCK = re.compile(
    r"(?is)<([a-z][a-z0-9:-]*)\b([^>]*)>(.*?)</\1\s*>"
)
_FOOTER = re.compile(
    r"(?i)(?:note|hinweis|notiz|nota)\s+(?:for|pour|per|f[uü]r|ans)\b"
    r".{0,80}?(?:model|modell|mod[eè]le|assistant|assistente|\bki\b|\bai\b)"
    r"|assistant reading|mod[eè]le qui|modell,? das diese|modello che"
)


def normalize(text: str) -> tuple[str, list[int]]:
    """Lowercase, drop accents, and turn apostrophes into spaces.

    ``mapping[i]`` is the index in ``text`` that produced normalised
    character ``i``. ``ß`` becomes ``ss``, so one original character can
    own two normalised characters.
    """
    chars: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(text):
        if char in {"'", "’", "`", "-", "‐"}:
            chars.append(" ")
            mapping.append(index)
            continue
        pieces = unicodedata.normalize("NFD", char)
        base = [item for item in pieces if unicodedata.category(item) != "Mn"]
        if not base:
            continue
        piece = "".join(base).lower().replace("ß", "ss")
        for item in piece:
            chars.append(item)
            mapping.append(index)
    return "".join(chars), mapping


def _fold_term(term: str) -> str:
    folded, _mapping = normalize(term)
    return " ".join(folded.split())


def _compile(terms: Sequence[str]) -> Optional[re.Pattern[str]]:
    cleaned = sorted({_fold_term(term) for term in terms if term.strip()}, key=len, reverse=True)
    if not cleaned:
        return None
    body = "|".join(re.escape(term) for term in cleaned)
    return re.compile(rf"(?<![a-z0-9])(?:{body})(?![a-z0-9])")


# Compiled once. Each pattern is tied to a language so a scan can ignore packs
# the caller turned off.
_COMPILED: dict[str, dict[str, re.Pattern[str]]] = {}
for _group, _by_lang in _LEXICON.items():
    _COMPILED[_group] = {}
    for _language, _terms in _by_lang.items():
        _pattern = _compile(_terms)
        if _pattern is not None:
            _COMPILED[_group][_language] = _pattern


def hidden_regions(text: str) -> list[tuple[int, int]]:
    """Spans where a reader would not see the words, plus mail notes to a model."""
    regions: list[tuple[int, int]] = []
    for match in _COMMENT.finditer(text):
        regions.append((match.start(1), match.end(1)))
    for match in _TAG_BLOCK.finditer(text):
        attrs = match.group(2)
        if _HIDDEN_MARK.search(attrs):
            regions.append((match.start(3), match.end(3)))
    for match in _FOOTER.finditer(text):
        end = text.find("\n\n", match.start())
        if end < 0:
            end = len(text)
        regions.append((match.start(), end))
    return regions


def _overlaps(start: int, end: int, regions: Sequence[tuple[int, int]]) -> bool:
    for region_start, region_end in regions:
        if end > region_start and start < region_end:
            return True
    return False


def _languages(languages: Optional[Sequence[str]]) -> tuple[str, ...]:
    if languages is None:
        return KNOWN_LANGUAGES
    return tuple(code for code in expand_languages(languages) if code in KNOWN_LANGUAGES)


class _Hit:
    __slots__ = ("token_start", "token_end", "group", "norm_start", "norm_end", "language")

    def __init__(self, token_start, token_end, group, norm_start, norm_end, language):
        self.token_start = token_start
        self.token_end = token_end
        self.group = group
        self.norm_start = norm_start
        self.norm_end = norm_end
        self.language = language


def _token_at(tokens: list[tuple[int, int]], index: int) -> int:
    """Index of the token that covers normalised offset ``index``."""
    for position, (start, end) in enumerate(tokens):
        if start <= index < end:
            return position
    if tokens and index >= tokens[-1][1]:
        return len(tokens) - 1
    return 0


def _decide(groups: set[str]) -> Optional[tuple[str, str, set[str]]]:
    """Return the strongest category justified by ``groups``."""
    options: list[tuple[str, str, set[str]]] = []
    if "override_verb" in groups and "target_noun" in groups:
        severity = "high" if "earlier" in groups else "low"
        options.append(
            ("instruction_override", severity, {"override_verb", "target_noun", "earlier"})
        )
    if "exfil_verb" in groups and "exfil_noun" in groups:
        options.append(("data_exfiltration", "high", {"exfil_verb", "exfil_noun"}))
    if "role_verb" in groups and "role_noun" in groups:
        options.append(("role_impersonation", "high", {"role_verb", "role_noun"}))
    if "tool_phrase" in groups:
        options.append(("tool_abuse", "medium", {"tool_phrase"}))
    elif "tool_verb" in groups and "tool_noun" in groups:
        options.append(("tool_abuse", "medium", {"tool_verb", "tool_noun"}))
    if not options:
        return None
    rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    options.sort(key=lambda item: rank[item[1]], reverse=True)
    return options[0]


def scan_intent(
    text: str,
    languages: Optional[Sequence[str]] = None,
    *,
    window: int = DEFAULT_WINDOW,
    hidden: Optional[Sequence[tuple[int, int]]] = None,
) -> list[Finding]:
    """Find co-occurring intent words and return findings in ``text``."""
    if window < 2:
        raise ValueError("intent window must be at least 2.")
    normalised, mapping = normalize(text)
    if not normalised:
        return []
    tokens = [(match.start(), match.end()) for match in _TOKEN.finditer(normalised)]
    if not tokens:
        return []
    codes = _languages(languages)
    hits: list[_Hit] = []
    for group, by_lang in _COMPILED.items():
        for language in codes:
            pattern = by_lang.get(language)
            if pattern is None:
                continue
            for match in pattern.finditer(normalised):
                hits.append(
                    _Hit(
                        _token_at(tokens, match.start()),
                        _token_at(tokens, match.end() - 1),
                        group,
                        match.start(),
                        match.end(),
                        language,
                    )
                )
    if not hits:
        return []
    hits.sort(key=lambda hit: (hit.token_start, hit.norm_start, hit.group))
    regions = list(hidden) if hidden is not None else hidden_regions(text)
    findings: list[Finding] = []
    covered_until = -1
    for index, left in enumerate(hits):
        if left.norm_start < covered_until:
            continue
        window_hits = [
            hit
            for hit in hits
            if left.token_start <= hit.token_start <= left.token_start + window - 1
        ]
        decided = _decide({hit.group for hit in window_hits})
        if decided is None:
            continue
        category, severity, used_groups = decided
        used = [hit for hit in window_hits if hit.group in used_groups]
        if not used:
            continue
        norm_start = min(hit.norm_start for hit in used)
        norm_end = max(hit.norm_end for hit in used)
        if norm_start < covered_until:
            continue
        origin_start = mapping[norm_start]
        origin_end = mapping[norm_end - 1] + 1
        if _overlaps(origin_start, origin_end, regions) and severity != "critical":
            severity = _UP[severity]
        language = used[0].language
        extra = ""
        if "earlier" in {hit.group for hit in used} and category == "instruction_override":
            extra = " It also points at something from earlier in the context."
        findings.append(
            make_finding(
                text,
                origin_start,
                origin_end,
                rule_id=_RULES[category],
                category=category,
                severity=severity,
                explanation=_EXPLANATION[category] + extra,
                language=language,
            )
        )
        covered_until = norm_end
        del index
    return findings


def span_has_intent(text: str, languages: Optional[Sequence[str]] = None) -> bool:
    """True when ``text`` itself contains an intent pair above ``low``."""
    return any(finding.severity != "low" for finding in scan_intent(text, languages))
