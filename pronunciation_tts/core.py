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
