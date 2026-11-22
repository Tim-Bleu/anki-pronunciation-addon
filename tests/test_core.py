import pytest

from pronunciation_tts import core

BASIC_FRONT = ["{{Front}}"]
BASIC_BACK = ["{{FrontSide}}<hr id=answer>{{Back}}"]
CLOZE_FRONT = ["{{cloze:Text}}"]
CLOZE_BACK = ["{{cloze:Text}}<br>{{Back Extra}}"]


def test_filename_deterministic_and_safe():
    a = core.media_filename("google_translate", "en-GB", "hello", False)
    assert a == core.media_filename("google_translate", "en-GB", "hello", False)
    assert a != core.media_filename("google_translate", "en-US", "hello", False)
    assert a != core.media_filename("google_translate", "en-GB", "hello", True)
    assert a.startswith("pron_en-GB_") and a.endswith(".mp3")
    assert core.media_filename("x", "../../evil", "t", False).startswith("pron_evil_")


def test_insert_and_replace():
    f = core.insert_sound_tag("house", "pron_en-GB_aaa.mp3")
    assert f == "house [sound:pron_en-GB_aaa.mp3]"
    f2 = core.insert_sound_tag(f, "pron_en-US_bbb.mp3")
    assert f2 == "house [sound:pron_en-US_bbb.mp3]"
    f3 = core.insert_sound_tag(f, "pron_en-US_bbb.mp3", replace_existing=False)
    assert f3.count("[sound:") == 2
    assert core.insert_sound_tag("", "pron_x.mp3") == "[sound:pron_x.mp3]"
    # foreign sound tags are never touched
    assert "[sound:mine.mp3]" in core.insert_sound_tag("[sound:mine.mp3]", "pron_x.mp3")
    # idempotent
    assert core.insert_sound_tag(f, "pron_en-GB_aaa.mp3", False) == f


def test_insert_rejects_unsafe_filename():
    with pytest.raises(ValueError):
        core.insert_sound_tag("", "a]b.mp3")


def test_referenced_fields():
    t = "{{#Audio}}{{Audio}}{{/Audio}} {{text:Word}} {{cloze:Text}} {{^X}}{{/X}} {{!c}}"
    assert core.referenced_fields(t) == {"Audio", "Word", "Text"}


def test_conditional_only_is_not_on_front():
    assert not core.field_on_front("Back", ["{{#Back}}has back{{/Back}}"])


def test_default_basic():
    assert core.default_fields(["Front", "Back"], BASIC_FRONT, BASIC_BACK, False) == ("Back", "Back")


def test_default_basic_with_audio_field():
    back = ["{{FrontSide}}{{Back}}{{Audio}}"]
    assert core.default_fields(["Front", "Back", "Audio"], BASIC_FRONT, back, False) == ("Back", "Audio")


def test_default_cloze():
    assert core.default_fields(["Text", "Back Extra"], CLOZE_FRONT, CLOZE_BACK, True) == (
        "Text",
        "Back Extra",
    )
