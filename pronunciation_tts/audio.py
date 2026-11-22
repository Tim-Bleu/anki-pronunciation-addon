"""Validation of downloaded audio data. Pure Python."""

from __future__ import annotations

MIN_AUDIO_BYTES = 64
MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MiB is plenty for a sentence


class InvalidAudioError(Exception):
    pass


def looks_like_mp3(data: bytes) -> bool:
    """Check the magic bytes of an MP3 file (ID3 tag or MPEG frame sync)."""
    if len(data) < 3:
        return False
    if data[:3] == b"ID3":
        return True
    # MPEG audio frame header: 11 set sync bits, layer != 0 ("reserved")
    return data[0] == 0xFF and (data[1] & 0xE0) == 0xE0 and (data[1] & 0x06) != 0


def validate_mp3(data: bytes) -> bytes:
    """Return ``data`` unchanged if it is a plausible MP3, else raise."""
    if not isinstance(data, (bytes, bytearray)):
        raise InvalidAudioError("Audio-Daten haben einen ungültigen Typ.")
    if len(data) < MIN_AUDIO_BYTES:
        raise InvalidAudioError("Die heruntergeladene Audiodatei ist leer oder zu klein.")
    if len(data) > MAX_AUDIO_BYTES:
        raise InvalidAudioError("Die heruntergeladene Audiodatei ist zu groß.")
    if not looks_like_mp3(data):
        raise InvalidAudioError("Die heruntergeladene Datei ist keine gültige MP3-Datei.")
    return bytes(data)
