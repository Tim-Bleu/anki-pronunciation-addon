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


# ---------------------------------------------------------------- audio inside clozes

CLOZE = "Stop being so {{c1::petty::kleinlich}}."


def test_cloze_answers():
    assert core.cloze_answers(CLOZE + " {{c2::<b>Now</b>}}") == [(1, "petty"), (2, "Now")]
    assert core.cloze_numbers("{{c1::a}} {{c1::b}} {{c3::c}}") == {1, 3}
    assert core.cloze_answers("no cloze") == []


def test_insert_in_cloze_keeps_hint():
    out = core.insert_sound_in_clozes(CLOZE, lambda n, t, f: "pron_a.mp3")
    assert out == "Stop being so {{c1::petty [sound:pron_a.mp3]::kleinlich}}."


def test_insert_in_cloze_without_hint_and_replace():
    out = core.insert_sound_in_clozes("{{c1::petty}}", lambda n, t, f: "pron_a.mp3")
    assert out == "{{c1::petty [sound:pron_a.mp3]}}"
    again = core.insert_sound_in_clozes(out, lambda n, t, f: "pron_b.mp3")
    assert again == "{{c1::petty [sound:pron_b.mp3]}}"
    kept = core.insert_sound_in_clozes(out, lambda n, t, f: "pron_b.mp3", replace_existing=False)
    assert kept.count("[sound:") == 2


def test_insert_in_cloze_first_of_number_only():
    out = core.insert_sound_in_clozes(
        "{{c1::a}} {{c1::b}} {{c2::c}}", lambda n, t, first: f"pron_{n}.mp3" if first else None
    )
    assert out == "{{c1::a [sound:pron_1.mp3]}} {{c1::b}} {{c2::c [sound:pron_2.mp3]}}"


def test_insert_in_cloze_word_receives_answer_text():
    seen = []
    core.insert_sound_in_clozes(CLOZE, lambda n, t, f: seen.append((n, t, f)))
    assert seen == [(1, "petty", True)]


def test_insert_in_cloze_keeps_user_audio_and_rejects_unsafe():
    out = core.insert_sound_in_clozes("{{c1::x [sound:mine.mp3]}}", lambda *a: "pron_a.mp3")
    assert "[sound:mine.mp3]" in out and "[sound:pron_a.mp3]" in out
    with pytest.raises(ValueError):
        core.insert_sound_in_clozes("{{c1::x}}", lambda *a: "a]b.mp3")


def test_speech_text_ignores_inserted_audio():
    from pronunciation_tts.text import field_to_speech_text

    out = core.insert_sound_in_clozes(CLOZE, lambda *a: "pron_a.mp3")
    assert field_to_speech_text(out) == field_to_speech_text(CLOZE) == "Stop being so petty."


def test_field_is_cloze_rendered():
    assert core.field_is_cloze_rendered("Text", ["{{cloze:Text}}"])
    assert core.field_is_cloze_rendered("Text", ["{{furigana:cloze:Text}}"])
    assert not core.field_is_cloze_rendered("Text", ["{{Text}}"])
    assert not core.field_is_cloze_rendered("Back Extra", ["{{cloze:Text}}"])
