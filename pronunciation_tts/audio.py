"""Validation of downloaded audio data. Pure Python."""

from __future__ import annotations

from .i18n import tr

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
        raise InvalidAudioError(tr("audio.bad_type"))
    if len(data) < MIN_AUDIO_BYTES:
        raise InvalidAudioError(tr("audio.too_small"))
    if len(data) > MAX_AUDIO_BYTES:
        raise InvalidAudioError(tr("audio.too_big"))
    if not looks_like_mp3(data):
        raise InvalidAudioError(tr("audio.not_mp3"))
    return bytes(data)
