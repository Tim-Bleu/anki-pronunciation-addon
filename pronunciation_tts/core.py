"""Note/field/template logic independent of the Anki GUI. Pure Python."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

FILE_PREFIX = "pron_"
_OWN_SOUND_RE = re.compile(r"\s*\[sound:" + FILE_PREFIX + r"[A-Za-z0-9_-]+\.mp3\]")
_TEMPLATE_TAG_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
_AUDIO_FIELD_NAMES = ("audio", "sound", "aussprache", "pronunciation", "ton", "tts")


def media_filename(provider_id: str, voice_id: str, text: str, slow: bool) -> str:
    """Deterministic, filesystem-safe name -> identical requests reuse the file."""
    digest = hashlib.sha256(f"{provider_id}\0{voice_id}\0{int(slow)}\0{text}".encode()).hexdigest()[:20]
    safe_voice = re.sub(r"[^A-Za-z0-9-]", "", voice_id)
    return f"{FILE_PREFIX}{safe_voice}_{digest}.mp3"


def insert_sound_tag(field_html: str, filename: str, replace_existing: bool = True) -> str:
    """Append ``[sound:filename]`` to the field (optionally replacing our old tags)."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename):
        raise ValueError("unsafe media filename")
    html = field_html or ""
    if replace_existing:
        html = _OWN_SOUND_RE.sub("", html)
    tag = f"[sound:{filename}]"
    if tag in html:
        return html
    html = html.rstrip()
    return f"{html} {tag}" if html else tag


def referenced_fields(template: str) -> set[str]:
    """Field names whose *content* is rendered by a card template.

    Conditionals (``{{#F}}``, ``{{^F}}``, ``{{/F}}``) and comments do not
    render the content and are ignored. Filters like ``{{text:F}}`` or
    ``{{cloze:F}}`` are resolved to ``F``.
    """
    names: set[str] = set()
    for raw in _TEMPLATE_TAG_RE.findall(template or ""):
        tag = raw.strip()
        if not tag or tag[0] in "#^/!":
            continue
        names.add(tag.split(":")[-1].strip())
    return names


def field_on_front(field: str, front_templates: Sequence[str]) -> bool:
    return any(field in referenced_fields(t) for t in front_templates)


def field_on_back(field: str, back_templates: Sequence[str]) -> bool:
    return any(field in referenced_fields(t) for t in back_templates)


def default_fields(
    field_names: Sequence[str],
    front_templates: Sequence[str],
    back_templates: Sequence[str],
    is_cloze: bool,
) -> tuple[str, str]:
    """Guess (source_field, target_field) for a note type."""
    if not field_names:
        raise ValueError("note type has no fields")
    back_only = [
        f
        for f in field_names
        if not field_on_front(f, front_templates) and field_on_back(f, back_templates)
    ]

    if is_cloze:
        source = field_names[0]
    else:
        candidates = [f for f in back_only if f.lower() not in _AUDIO_FIELD_NAMES]
        source = candidates[0] if candidates else field_names[min(1, len(field_names) - 1)]

    for f in field_names:
        if f.lower() in _AUDIO_FIELD_NAMES and not field_on_front(f, front_templates):
            return source, f
    if source in back_only:
        return source, source
    for preferred in ("Back Extra", "Rückseite Extra", "Extra"):
        if preferred in back_only:
            return source, preferred
    if back_only:
        return source, back_only[0]
    return source, source


# ---------------------------------------------------------------- audio inside cloze deletions
#
# ``{{c1::petty [sound:x.mp3]::kleinlich}}``: on card 1 the deletion is hidden on
# the front, so Anki only plays x.mp3 on the back. Caveat: on *other* cards
# (c2, c3 …) this deletion is shown as plain text on the front, so its audio
# plays there too. That only repeats the visible word and never reveals the
# answer of the card being studied. With several cloze numbers each deletion
# gets only its own word (``effective_cloze_text``).

_NB = r"(?:(?!\{\{|\}\}).)*?"
_CLOZE_PARTS_RE = re.compile(r"\{\{c(\d+)::(" + _NB + r")(?:::(" + _NB + r"))?\}\}", re.DOTALL)

PLACEMENT_FIELD = "field"
PLACEMENT_CLOZE = "cloze"
CLOZE_TEXT_SENTENCE = "sentence"
CLOZE_TEXT_WORD = "word"


def strip_own_sound_tags(field_html: str) -> str:
    return _OWN_SOUND_RE.sub("", field_html or "")


def cloze_answers(field_html: str) -> list[tuple[int, str]]:
    """``(cloze number, spoken answer text)`` for every (innermost) deletion, in order."""
    from .text import field_to_speech_text

    return [
        (int(m.group(1)), field_to_speech_text(m.group(2)))
        for m in _CLOZE_PARTS_RE.finditer(field_html or "")
    ]


def cloze_numbers(field_html: str) -> set[int]:
    return {num for num, _ in cloze_answers(field_html)}


def effective_cloze_text(field_html: str, setting: str) -> str:
    """Several cloze numbers (c1, c2 …) mean several foreign words: then every
    deletion gets only the audio of its own word. Otherwise ``setting`` applies."""
    return CLOZE_TEXT_WORD if len(cloze_numbers(field_html)) > 1 else setting


def insert_sound_in_clozes(field_html: str, pick, replace_existing: bool = True) -> str:
    """Put a sound tag at the end of each deletion's answer (before ``::hint``).

    ``pick(number, answer_text, first_of_number)`` returns the media filename
    for that deletion, or ``None`` to leave it untouched.
    """
    from .text import field_to_speech_text

    html = strip_own_sound_tags(field_html) if replace_existing else (field_html or "")
    seen: set[int] = set()

    def repl(m: re.Match) -> str:
        num = int(m.group(1))
        answer, hint = m.group(2), m.group(3)
        first = num not in seen
        seen.add(num)
        fname = pick(num, field_to_speech_text(answer), first)
        if fname:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", fname):
                raise ValueError("unsafe media filename")
            tag = f"[sound:{fname}]"
            if tag not in answer:
                answer = f"{answer.rstrip()} {tag}" if answer.strip() else tag
        hint_part = f"::{hint}" if hint is not None else ""
        return f"{{{{c{num}::{answer}{hint_part}}}}}"

    return _CLOZE_PARTS_RE.sub(repl, html)


def field_is_cloze_rendered(field: str, front_templates) -> bool:
    """True if a front template renders ``field`` with the ``cloze:`` filter."""
    for t in front_templates:
        for raw in _TEMPLATE_TAG_RE.findall(t or ""):
            parts = [p.strip() for p in raw.strip().split(":")]
            if len(parts) >= 2 and parts[-1] == field and "cloze" in parts[:-1]:
                return True
    return False


# ---------------------------------------------------------------- per-cloze audio field
#
# Only the *current* cloze's audio, only on the back: the audio lives in its own
# field, wrapped in matching cloze numbers,
#     Cloze Audio = "{{c1::[sound:petty.mp3]}} {{c2::[sound:rude.mp3]}}"
# and the back template renders it with ``{{cloze-only:Cloze Audio}}``, which
# outputs just the active deletion. The front never shows the field.

PLACEMENT_CLOZE_FIELD = "cloze_field"
PLACEMENTS = (PLACEMENT_FIELD, PLACEMENT_CLOZE, PLACEMENT_CLOZE_FIELD)
CLOZE_PLACEMENTS = (PLACEMENT_CLOZE, PLACEMENT_CLOZE_FIELD)
CLOZE_AUDIO_FIELD = "Cloze Audio"


def cloze_only_on_back(field: str, back_templates) -> bool:
    """True if a back template renders ``field`` with the ``cloze-only:`` filter."""
    for t in back_templates:
        for raw in _TEMPLATE_TAG_RE.findall(t or ""):
            parts = [p.strip() for p in raw.strip().split(":")]
            if len(parts) >= 2 and parts[-1] == field and "cloze-only" in parts[:-1]:
                return True
    return False


def add_cloze_only(back_template: str, field: str = CLOZE_AUDIO_FIELD) -> str:
    """Append ``{{cloze-only:field}}`` to a back template (idempotent)."""
    if cloze_only_on_back(field, [back_template]):
        return back_template
    return f"{(back_template or '').rstrip()}\n\n{{{{cloze-only:{field}}}}}"


def build_cloze_audio(text_html: str, cloze_text: str, stored: dict, sentence: str = "") -> str:
    """Content of the per-cloze audio field for the clozes in ``text_html``.

    ``stored`` maps spoken text -> media filename. In ``word`` mode each deletion
    gets the file of its own answer; in ``sentence`` mode every cloze number gets
    the file of ``sentence``.
    """
    parts: list[str] = []
    seen: set[tuple[int, str]] = set()
    for num, answer in cloze_answers(text_html):
        fname = stored.get(answer if cloze_text == CLOZE_TEXT_WORD else sentence)
        if not fname or (num, fname) in seen:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", fname):
            raise ValueError("unsafe media filename")
        seen.add((num, fname))
        parts.append(f"{{{{c{num}::[sound:{fname}]}}}}")
    return " ".join(parts)
