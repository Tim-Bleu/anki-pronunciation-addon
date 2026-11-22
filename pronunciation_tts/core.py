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
# would play there – callers warn about notes with several cloze numbers.

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
