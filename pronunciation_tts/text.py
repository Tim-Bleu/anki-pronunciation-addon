"""Turn raw Anki field HTML into plain text suitable for speech synthesis.

Pure Python, no aqt/anki imports.
"""

from __future__ import annotations

import html
import re

# {{c1::answer}} / {{c1::answer::hint}} ; answers may span lines
_NO_BRACES = r"(?:(?!\{\{|\}\}).)*?"
_CLOZE_RE = re.compile(r"\{\{c\d+::(" + _NO_BRACES + r")(?:::" + _NO_BRACES + r")?\}\}", re.DOTALL)
# leading whitespace included so "petty [sound:x.mp3]." -> "petty."
_SOUND_RE = re.compile(r"\s*\[sound:[^\]]*\](?=(\w)?)")
_BR_RE = re.compile(r"<\s*(br|/p|/div|/li)\b[^>]*>", re.IGNORECASE)
_STYLE_SCRIPT_RE = re.compile(r"<(style|script)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def field_to_speech_text(field_html: str) -> str:
    """Strip HTML, sound tags and cloze markup; return clean plain text.

    Cloze deletions are replaced by their answer, so the complete sentence
    is spoken (the audio lives on the back side, i.e. after the answer is
    revealed).
    """
    text = field_html or ""
    # Innermost clozes first; repeat so nested ones ({{c1::a {{c2::b}}}}) resolve too.
    for _ in range(5):
        new = _CLOZE_RE.sub(r"\1", text)
        if new == text:
            break
        text = new
    text = _SOUND_RE.sub(lambda m: " " if m.group(1) else "", text)
    text = _STYLE_SCRIPT_RE.sub(" ", text)
    text = _BR_RE.sub(" ", text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text).replace(" ", " ")
    return _WS_RE.sub(" ", text).strip()


_SPLIT_PUNCT = re.compile(r"(?<=[.!?;:,。！？；：，、])\s*")


def split_text(text: str, max_len: int) -> list[str]:
    """Split ``text`` into chunks of at most ``max_len`` characters.

    Prefer splitting at punctuation, then at whitespace; hard-split only
    if a single word is longer than ``max_len``.
    """
    if max_len < 1:
        raise ValueError("max_len must be >= 1")
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""

    def push(piece: str) -> None:
        nonlocal current
        piece = piece.strip()
        if not piece:
            return
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= max_len:
            current = candidate
            return
        if current:
            chunks.append(current)
            current = ""
        if len(piece) <= max_len:
            current = piece
            return
        # piece itself too long: split on whitespace
        words = piece.split(" ")
        if len(words) > 1:
            for w in words:
                push(w)
            return
        # one huge word: hard split
        for i in range(0, len(piece), max_len):
            part = piece[i : i + max_len]
            if len(part) == max_len:
                chunks.append(part)
            else:
                current = part

    for sentence in _SPLIT_PUNCT.split(text):
        push(sentence)
    if current:
        chunks.append(current)
    return chunks
