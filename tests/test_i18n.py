import re

import pytest

from pronunciation_tts import i18n
from pronunciation_tts.voices import VOICES

PLACEHOLDER = re.compile(r"(?<!\{)\{(\w+)[^{}]*\}(?!\})")


@pytest.fixture(autouse=True)
def reset_language():
    yield
    i18n.set_language("en")


def test_every_message_has_both_languages_with_same_placeholders():
    for key, entry in i18n.MESSAGES.items():
        assert set(entry) == {"en", "de"}, key
        assert set(PLACEHOLDER.findall(entry["en"])) == set(PLACEHOLDER.findall(entry["de"])), key


def test_messages_format():
    for key, entry in i18n.MESSAGES.items():
        names = set(PLACEHOLDER.findall(entry["en"]))
        for lang in ("en", "de"):
            i18n.set_language(lang)
            i18n.tr(key, **{n: "X" for n in names}) if names else i18n.tr(key)


def test_brace_escaping():
    assert "{{cloze:Text}}" in i18n.tr("dlg.not_cloze_field", f="Text")
    assert "<code>{{Audio}}</code>" in i18n.tr("dlg.not_on_back", f="Audio")
    assert "{{c1::…}}" in i18n.tr("ed.no_cloze", f="Text")


@pytest.mark.parametrize(
    "setting, anki, expected",
    [("auto", "de_DE", "de"), ("auto", "de", "de"), ("auto", "en_US", "en"), ("auto", "fr_FR", "en"),
     (None, None, "en"), ("de", "en_US", "de"), ("en", "de_DE", "en"), ("xx", "de_DE", "de")],
)
def test_resolve_language(setting, anki, expected):
    assert i18n.resolve_language(setting, anki) == expected


def test_switching_language():
    i18n.set_language("de")
    assert i18n.tr("ed.done") == "Aussprache eingefügt."
    assert VOICES[1].label == "Englisch (Britisch)"
    i18n.set_language("en")
    assert i18n.tr("ed.done") == "Pronunciation inserted."
    assert VOICES[1].label == "English (British)"
    i18n.set_language("fr")
    assert i18n.current_language() == "en"
