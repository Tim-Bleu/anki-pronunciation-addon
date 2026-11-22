from pronunciation_tts.text import field_to_speech_text, split_text


def test_strips_html_entities_and_sound():
    raw = "<b>Hello</b>&nbsp;world<br>again [sound:old.mp3] &amp; more"
    assert field_to_speech_text(raw) == "Hello world again & more"


def test_cloze_answer_is_spoken():
    raw = "I {{c1::have been::aux}} to {{c2::London}}."
    assert field_to_speech_text(raw) == "I have been to London."


def test_nested_cloze():
    assert field_to_speech_text("{{c1::a {{c2::b}} c}}") == "a b c"


def test_style_script_removed():
    assert field_to_speech_text("<style>x{}</style>Hi<script>alert(1)</script>") == "Hi"


def test_split_short():
    assert split_text("hello", 100) == ["hello"]


def test_split_respects_limit_and_keeps_words():
    text = "This is a sentence. " * 20
    chunks = split_text(text, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_split_long_word():
    chunks = split_text("x" * 250, 100)
    assert [len(c) for c in chunks] == [100, 100, 50]


def test_split_empty():
    assert split_text("   ", 10) == []
