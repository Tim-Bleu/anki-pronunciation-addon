import pytest

from pronunciation_tts.audio import InvalidAudioError, looks_like_mp3, validate_mp3

MP3 = b"ID3" + b"\x00" * 100
FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 100


def test_valid():
    assert validate_mp3(MP3) == MP3
    assert validate_mp3(FRAME) == FRAME


@pytest.mark.parametrize("data", [b"", b"ID3", b"<html>" + b"x" * 100, b"\x00" * 200])
def test_invalid(data):
    with pytest.raises(InvalidAudioError):
        validate_mp3(data)


def test_too_big():
    with pytest.raises(InvalidAudioError):
        validate_mp3(b"ID3" + b"\x00" * (6 * 1024 * 1024))


def test_magic():
    assert not looks_like_mp3(b"\xff\xe0")
    assert not looks_like_mp3(b"\xff\xe1\x00")  # layer bits reserved
