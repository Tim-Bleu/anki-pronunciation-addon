"""Smoke tests against the real ``anki``/``aqt`` packages.

Skipped unless anki + aqt (+ PyQt6) are installed, e.g.:
    pip install aqt[qt6] anki
    QT_QPA_PLATFORM=offscreen pytest tests/test_anki_integration.py
"""

import importlib
import os
import sys
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
anki_collection = pytest.importorskip("anki.collection")
aqt = pytest.importorskip("aqt")

from pronunciation_tts import core  # noqa: E402

MP3 = b"ID3" + b"\x01" * 200


@pytest.fixture
def col(tmp_path):
    c = anki_collection.Collection(str(tmp_path / "c.anki2"))
    yield c
    c.close()


def _nt_parts(nt):
    return (
        [f["name"] for f in nt["flds"]],
        [t["qfmt"] for t in nt["tmpls"]],
        [t["afmt"] for t in nt["tmpls"]],
    )


def test_defaults_on_stock_notetypes(col):
    fields, fronts, backs = _nt_parts(col.models.by_name("Basic"))
    assert core.default_fields(fields, fronts, backs, False) == ("Back", "Back")
    fields, fronts, backs = _nt_parts(col.models.by_name("Cloze"))
    assert core.default_fields(fields, fronts, backs, True) == ("Text", "Back Extra")
    # "Basic (and reversed card)": Back is on a front side -> must not be chosen as target
    fields, fronts, backs = _nt_parts(col.models.by_name("Basic (and reversed card)"))
    _src, target = core.default_fields(fields, fronts, backs, False)
    assert core.field_on_front(target, fronts)  # no safe field exists; dialog will block


@pytest.fixture
def integration(col, monkeypatch):
    from aqt.qt import QApplication

    app = QApplication.instance() or QApplication([])
    cfg = {
        "provider": "google_translate",
        "default_voice": "en-GB",
        "replace_existing_audio": True,
        "play_after_insert": True,
        "note_types": {},
    }
    mw = types.SimpleNamespace(
        col=col,
        addonManager=types.SimpleNamespace(
            addonFromModule=lambda name: name.split(".")[0],
            getConfig=lambda name: cfg,
            writeConfig=lambda name, c: cfg.update(c),
        ),
    )
    monkeypatch.setattr(aqt, "mw", mw)
    sys.modules.pop("pronunciation_tts.editor_integration", None)
    ei = importlib.import_module("pronunciation_tts.editor_integration")

    class SyncOp:
        def __init__(self, *, parent, op, success):
            self.op, self.success, self.fail = op, success, None

        def failure(self, f):
            self.fail = f
            return self

        def with_progress(self, *_):
            return self

        def run_in_background(self):
            try:
                result = self.op(col)
            except Exception as e:  # noqa: BLE001
                self.fail(e)
            else:
                self.success(result)

    played, warnings, updated = [], [], []
    monkeypatch.setattr(ei, "QueryOp", SyncOp)
    monkeypatch.setattr(ei.av_player, "play_tags", lambda tags: played.extend(t.filename for t in tags))
    monkeypatch.setattr(ei, "tooltip", lambda *a, **k: None)
    monkeypatch.setattr(ei, "showWarning", lambda msg, **k: warnings.append(msg))

    class FakeUpdate:
        def __init__(self, note):
            self.note = note

        def run_in_background(self, **_):
            col.update_note(self.note)
            updated.append(self.note.id)

    monkeypatch.setattr(ei, "update_note", lambda *, parent, note: FakeUpdate(note))

    class FakeProvider:
        id = "google_translate"
        calls = []

        def synthesize(self, text, voice, slow=False):
            self.calls.append((text, voice.id))
            return MP3

    provider = FakeProvider()
    monkeypatch.setattr(ei, "make_provider", lambda c: provider)
    return types.SimpleNamespace(
        ei=ei, cfg=cfg, played=played, warnings=warnings, updated=updated, provider=provider, app=app
    )


def _editor(note, add_mode):
    from aqt.qt import QWidget

    e = types.SimpleNamespace(note=note, addMode=add_mode, widget=QWidget(), reloaded=0)
    e.loadNoteKeepingFocus = lambda: setattr(e, "reloaded", e.reloaded + 1)
    return e


def test_generate_basic_existing_note(col, integration):
    ei = integration.ei
    nt = col.models.by_name("Basic")
    note = col.new_note(nt)
    note["Front"] = "das Haus"
    note["Back"] = "the <b>house</b>"
    col.add_note(note, col.decks.id("Default"))

    settings = ei.NoteTypeSettings(source="Back", target="Back", voice="en-GB")
    ei._run(_editor(note, False), note, settings, integration.cfg)

    assert integration.warnings == []
    assert integration.provider.calls == [("the house", "en-GB")]
    fresh = col.get_note(note.id)
    assert fresh["Back"].startswith("the <b>house</b> [sound:pron_en-GB_")
    fname = fresh["Back"].split("[sound:")[1].rstrip("]")
    assert col.media.have(fname)
    assert integration.played == [fname]
    assert integration.updated == [note.id]

    # second run: cached file, tag replaced not duplicated, no new download
    ei._run(_editor(fresh, False), fresh, settings, integration.cfg)
    assert len(integration.provider.calls) == 1
    assert col.get_note(note.id)["Back"].count("[sound:") == 1


def test_generate_cloze_add_mode(col, integration):
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "I {{c1::have been}} to London."
    editor = _editor(note, True)
    ei._run(editor, note, ei.NoteTypeSettings("Text", "Back Extra", "en-US"), integration.cfg)
    assert integration.provider.calls[-1] == ("I have been to London.", "en-US")
    assert note["Back Extra"].startswith("[sound:pron_en-US_")
    assert "[sound:" not in note["Text"]
    assert editor.reloaded == 1


def test_refuses_front_side_target(col, integration):
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "{{c1::x}}"
    ei._run(_editor(note, True), note, ei.NoteTypeSettings("Text", "Text", "en-US"), integration.cfg)
    assert integration.warnings and "front" in integration.warnings[0]
    assert integration.provider.calls == [] or integration.provider.calls[-1][0] != "x"


def test_settings_dialog_blocks_front_target(col, integration):
    from aqt.qt import QDialogButtonBox

    from pronunciation_tts.dialog import NoteTypeSettings, SettingsDialog

    nt = col.models.by_name("Cloze")
    fields, fronts, backs = _nt_parts(nt)
    dlg = SettingsDialog(None, fields, fronts, backs, NoteTypeSettings("Text", "Text", "en-GB"), "Cloze")
    ok = dlg.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert not ok.isEnabled()
    dlg.target.setCurrentText("Back Extra")
    assert ok.isEnabled()
    s = dlg.result_settings()
    assert (s.source, s.target, s.voice) == ("Text", "Back Extra", "en-GB")


def test_stored_settings_validation(col, integration):
    ei = integration.ei
    nt = col.models.by_name("Basic")
    fields = [f["name"] for f in nt["flds"]]
    cfg = {"note_types": {str(nt["id"]): {"source": "Back", "target": "Back", "voice": "en-GB"}}}
    assert ei._stored_settings(cfg, nt, fields).voice == "en-GB"
    cfg["note_types"][str(nt["id"])]["voice"] = "xx-XX"
    assert ei._stored_settings(cfg, nt, fields) is None
    cfg["note_types"][str(nt["id"])] = {"source": "Gone", "target": "Back", "voice": "en-GB"}
    assert ei._stored_settings(cfg, nt, fields) is None


def test_audio_inside_cloze_sentence(col, integration):
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "Stop being so {{c1::petty::kleinlich}}."
    col.add_note(note, col.decks.id("Default"))
    s = ei.NoteTypeSettings("Text", "Text", "en-GB", placement="cloze", cloze_text="sentence")
    ei._run(_editor(note, False), note, s, integration.cfg)

    assert integration.warnings == []
    assert integration.provider.calls == [("Stop being so petty.", "en-GB")]
    text = col.get_note(note.id)["Text"]
    fname = text.split("[sound:")[1].split("]")[0]
    assert text == f"Stop being so {{{{c1::petty [sound:{fname}]::kleinlich}}}}."

    # Real Anki rendering: no audio on the question, audio on the answer.
    card = col.get_note(note.id).cards()[0]
    assert card.question_av_tags() == []
    assert [t.filename for t in card.answer_av_tags()] == [fname]

    # rerun: cached and replaced, not duplicated
    fresh = col.get_note(note.id)
    ei._run(_editor(fresh, False), fresh, s, integration.cfg)
    assert len(integration.provider.calls) == 1
    assert col.get_note(note.id)["Text"].count("[sound:") == 1


def test_audio_inside_cloze_word_mode(col, integration):
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "Stop being so {{c1::petty::kleinlich}}, be {{c1::kind}}."
    s = ei.NoteTypeSettings("Text", "Text", "en-US", placement="cloze", cloze_text="word")
    ei._run(_editor(note, True), note, s, integration.cfg)
    assert integration.provider.calls == [("petty", "en-US"), ("kind", "en-US")]
    assert note["Text"].count("[sound:pron_en-US_") == 2
    assert "::kleinlich}}" in note["Text"]
    assert len(integration.played) == 2


def test_several_cloze_numbers_get_their_own_word(col, integration):
    """Rule: two cloze numbers = two foreign words -> each cloze gets only its own
    word, even if "whole sentence" is configured."""
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "Stop being so {{c1::petty::kleinlich}} and {{c2::rude::unhöflich}}."
    col.add_note(note, col.decks.id("Default"))
    s = ei.NoteTypeSettings("Text", "Text", "en-GB", placement="cloze", cloze_text="sentence")
    ei._run(_editor(note, False), note, s, integration.cfg)

    assert integration.warnings == []
    assert integration.provider.calls == [("petty", "en-GB"), ("rude", "en-GB")]
    text = col.get_note(note.id)["Text"]
    f_petty = core.media_filename("google_translate", "en-GB", "petty", False)
    f_rude = core.media_filename("google_translate", "en-GB", "rude", False)
    assert text == (
        f"Stop being so {{{{c1::petty [sound:{f_petty}]::kleinlich}}}} "
        f"and {{{{c2::rude [sound:{f_rude}]::unhöflich}}}}."
    )
    # Real rendering: on each card the hidden cloze's own word only plays on the back.
    c1, c2 = sorted(col.get_note(note.id).cards(), key=lambda c: c.ord)
    assert [t.filename for t in c1.question_av_tags()] == [f_rude]
    assert [t.filename for t in c2.question_av_tags()] == [f_petty]
    assert f_petty in [t.filename for t in c1.answer_av_tags()]
    assert f_rude in [t.filename for t in c2.answer_av_tags()]


def test_audio_inside_cloze_requires_cloze_field(col, integration):
    ei = integration.ei
    note = col.new_note(col.models.by_name("Cloze"))
    note["Text"] = "{{c1::x}}"
    note["Back Extra"] = "y"
    s = ei.NoteTypeSettings("Back Extra", "Text", "en-US", placement="cloze")
    ei._run(_editor(note, True), note, s, integration.cfg)
    assert integration.warnings and "cloze field" in integration.warnings[0]


def test_dialog_cloze_placement(col, integration):
    from aqt.qt import QDialogButtonBox

    from pronunciation_tts.dialog import NoteTypeSettings, SettingsDialog

    nt = col.models.by_name("Cloze")
    fields, fronts, backs = _nt_parts(nt)
    init = NoteTypeSettings("Text", "Text", "en-GB", placement="cloze", cloze_text="word")
    dlg = SettingsDialog(None, fields, fronts, backs, init, "Cloze", is_cloze=True)
    ok = dlg.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert ok.isEnabled()  # in-cloze placement allows the (front-side) cloze field
    s = dlg.result_settings()
    assert (s.placement, s.cloze_text) == ("cloze", "word")
    dlg.source.setCurrentText("Back Extra")
    assert not ok.isEnabled()

    # Basic note types do not offer the in-cloze option
    fields, fronts, backs = _nt_parts(col.models.by_name("Basic"))
    dlg2 = SettingsDialog(None, fields, fronts, backs, NoteTypeSettings("Back", "Back", "en-GB"), "Basic")
    assert dlg2.placement.count() == 1


def test_stored_settings_placement_validation(col, integration):
    ei = integration.ei
    basic, cloze = col.models.by_name("Basic"), col.models.by_name("Cloze")
    raw = {"source": "Text", "target": "Text", "voice": "en-GB", "placement": "cloze"}
    cfg = {"note_types": {str(cloze["id"]): raw}}
    assert ei._stored_settings(cfg, cloze, ["Text", "Back Extra"]).placement == "cloze"
    raw_basic = {"source": "Back", "target": "Back", "voice": "en-GB", "placement": "cloze"}
    cfg = {"note_types": {str(basic["id"]): raw_basic}}
    assert ei._stored_settings(cfg, basic, ["Front", "Back"]) is None
