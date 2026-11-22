"""Editor buttons, shortcuts and the background download."""

from __future__ import annotations

import os
from dataclasses import asdict

from anki.consts import MODEL_CLOZE
from anki.notes import Note
from anki.sound import SoundOrVideoTag
from aqt import gui_hooks, mw
from aqt.editor import Editor
from aqt.operations import QueryOp
from aqt.operations.note import update_note
from aqt.sound import av_player
from aqt.utils import askUser, showWarning, tooltip

from . import core
from .dialog import NoteTypeSettings, SettingsDialog
from .providers import PROVIDER_IDS, TTSError, make_provider
from .text import field_to_speech_text
from .voices import DEFAULT_VOICE_ID, get_voice, is_known_voice

ADDON_DIR = os.path.dirname(__file__)
ICON = os.path.join(ADDON_DIR, "icons", "speaker.svg")
ICON_SETTINGS = os.path.join(ADDON_DIR, "icons", "speaker_settings.svg")
ADDON_MODULE = mw.addonManager.addonFromModule(__name__)


# ---------------------------------------------------------------- config


def get_config() -> dict:
    cfg = mw.addonManager.getConfig(ADDON_MODULE) or {}
    cfg.setdefault("note_types", {})
    return cfg


def write_config(cfg: dict) -> None:
    mw.addonManager.writeConfig(ADDON_MODULE, cfg)


# ---------------------------------------------------------------- note type helpers


def _templates(note: Note) -> tuple[list[str], list[str], list[str], bool, dict]:
    nt = note.note_type()
    fields = [f["name"] for f in nt["flds"]]
    fronts = [t["qfmt"] for t in nt["tmpls"]]
    backs = [t["afmt"] for t in nt["tmpls"]]
    return fields, fronts, backs, nt["type"] == MODEL_CLOZE, nt


def _stored_settings(cfg: dict, nt: dict, fields: list[str]) -> NoteTypeSettings | None:
    raw = cfg["note_types"].get(str(nt["id"]))
    if not isinstance(raw, dict):
        return None
    try:
        s = NoteTypeSettings(
            source=str(raw["source"]),
            target=str(raw["target"]),
            voice=str(raw["voice"]),
            slow=bool(raw.get("slow", False)),
            provider=str(raw.get("provider", cfg.get("provider", "google_translate"))),
            placement=str(raw.get("placement", core.PLACEMENT_FIELD)),
            cloze_text=str(raw.get("cloze_text", core.CLOZE_TEXT_SENTENCE)),
        )
    except (KeyError, TypeError):
        return None
    if s.source not in fields or s.target not in fields or not is_known_voice(s.voice):
        return None
    if s.provider not in PROVIDER_IDS:
        return None
    if s.placement not in (core.PLACEMENT_FIELD, core.PLACEMENT_CLOZE):
        return None
    if s.placement == core.PLACEMENT_CLOZE and nt["type"] != MODEL_CLOZE:
        return None
    if s.cloze_text not in (core.CLOZE_TEXT_SENTENCE, core.CLOZE_TEXT_WORD):
        return None
    return s


def _default_settings(cfg: dict, fields, fronts, backs, is_cloze) -> NoteTypeSettings:
    source, target = core.default_fields(fields, fronts, backs, is_cloze)
    voice = cfg.get("default_voice", DEFAULT_VOICE_ID)
    if not is_known_voice(voice):
        voice = DEFAULT_VOICE_ID
    provider = cfg.get("provider", "google_translate")
    if provider not in PROVIDER_IDS:
        provider = "google_translate"
    return NoteTypeSettings(source, target, voice, bool(cfg.get("slow", False)), provider)


# ---------------------------------------------------------------- button actions


def on_generate(editor: Editor) -> None:
    note = editor.note
    if note is None:
        return
    cfg = get_config()
    fields, fronts, backs, _is_cloze, nt = _templates(note)
    settings = _stored_settings(cfg, nt, fields)
    if settings is None:
        on_settings(editor)
        return
    _run(editor, note, settings, cfg)


def on_settings(editor: Editor) -> None:
    note = editor.note
    if note is None:
        return
    cfg = get_config()
    fields, fronts, backs, is_cloze, nt = _templates(note)
    initial = _stored_settings(cfg, nt, fields) or _default_settings(cfg, fields, fronts, backs, is_cloze)
    dlg = SettingsDialog(editor.widget, fields, fronts, backs, initial, nt["name"], is_cloze=is_cloze)
    if not dlg.exec():
        return
    settings = dlg.result_settings()
    if dlg.remember.isChecked():
        cfg["note_types"][str(nt["id"])] = asdict(settings)
        write_config(cfg)
    _run(editor, note, settings, cfg)


def _run(editor: Editor, note: Note, settings: NoteTypeSettings, cfg: dict) -> None:
    _fields, fronts, _backs, is_cloze, _nt = _templates(note)
    replace = bool(cfg.get("replace_existing_audio", True))
    source_html = note[settings.source]

    if settings.placement == core.PLACEMENT_CLOZE:
        if not is_cloze or not core.field_is_cloze_rendered(settings.source, fronts):
            showWarning(
                f"„{settings.source}“ ist kein Lückentext-Feld. Bitte über den zweiten "
                "Lautsprecher-Knopf ein anderes Feld oder einen anderen Einfügeort wählen.",
                parent=editor.widget,
            )
            return
        answers = core.cloze_answers(source_html)
        if not answers:
            tooltip(f"Im Feld „{settings.source}“ wurde keine Lücke ({{{{c1::…}}}}) gefunden.", parent=editor.widget)
            return
        if len({n for n, _ in answers}) > 1 and not askUser(
            "Diese Notiz hat mehrere Lücken-Nummern (c1, c2 …). Auf der Karte einer Lücke sind "
            "die anderen Lücken sichtbar – deren Audio wäre dort schon auf der Vorderseite zu hören.\n\n"
            "Trotzdem in die Lücken einfügen?",
            parent=editor.widget,
            defaultno=True,
        ):
            return
        if settings.cloze_text == core.CLOZE_TEXT_WORD:
            texts = [t for _, t in answers if t]
        else:
            texts = [field_to_speech_text(source_html)]
    else:
        if core.field_on_front(settings.target, fronts):
            showWarning(
                f"Das Zielfeld „{settings.target}“ ist auf der Vorderseite sichtbar. "
                "Das Audio würde vor dem Aufdecken abgespielt. Bitte ein anderes Zielfeld wählen "
                "(zweiter Lautsprecher-Knopf).",
                parent=editor.widget,
            )
            return
        texts = [field_to_speech_text(source_html)]

    texts = list(dict.fromkeys(t for t in texts if t))  # unique, keep order
    if not texts:
        tooltip(f"Das Feld „{settings.source}“ ist leer.", parent=editor.widget)
        return

    try:
        voice = get_voice(settings.voice)
        provider = make_provider({**cfg, "provider": settings.provider})
    except (KeyError, TTSError) as e:
        showWarning(str(e), parent=editor.widget)
        return

    def op(col) -> dict[str, str]:
        stored: dict[str, str] = {}
        for text in texts:
            fname = core.media_filename(provider.id, voice.id, text, settings.slow)
            if not col.media.have(fname):  # else cached: same text, voice and speed
                fname = col.media.write_data(fname, provider.synthesize(text, voice, slow=settings.slow))
            stored[text] = fname
        return stored

    def transform(current: str, stored: dict[str, str]) -> str:
        if settings.placement == core.PLACEMENT_CLOZE:
            if settings.cloze_text == core.CLOZE_TEXT_WORD:
                return core.insert_sound_in_clozes(current, lambda _n, text, _f: stored.get(text), replace)
            sentence = stored[texts[0]]
            return core.insert_sound_in_clozes(current, lambda _n, _t, first: sentence if first else None, replace)
        return core.insert_sound_tag(current, stored[texts[0]], replace)

    def on_success(stored: dict[str, str]) -> None:
        field = settings.source if settings.placement == core.PLACEMENT_CLOZE else settings.target
        _apply(editor, note, field, lambda current: transform(current, stored))
        if cfg.get("play_after_insert", True):
            av_player.play_tags([SoundOrVideoTag(filename=f) for f in stored.values()])
        tooltip("Aussprache eingefügt.", parent=editor.widget)

    def on_failure(exc: Exception) -> None:
        showWarning(f"Aussprache konnte nicht erstellt werden:\n\n{exc}", parent=editor.widget)

    (
        QueryOp(parent=editor.widget, op=op, success=on_success)
        .failure(on_failure)
        .with_progress("Aussprache wird sicher heruntergeladen …")
        .run_in_background()
    )


def _apply(editor: Editor, note: Note, field: str, transform) -> None:
    if editor.note is not note:
        # The user switched to another note while downloading.
        if not note.id:
            return
        note = mw.col.get_note(note.id)
        note[field] = transform(note[field])
        update_note(parent=editor.widget, note=note).run_in_background()
        return

    note[field] = transform(note[field])
    if editor.addMode or not note.id:
        editor.loadNoteKeepingFocus()
    else:
        update_note(parent=editor.widget, note=note).run_in_background(initiator=editor)
        editor.loadNoteKeepingFocus()


# ---------------------------------------------------------------- hooks


def _add_buttons(buttons: list[str], editor: Editor) -> None:
    cfg = get_config()
    buttons.append(
        editor.addButton(
            icon=ICON,
            cmd="pronunciation_tts_generate",
            func=on_generate,
            tip=f"Aussprache einfügen ({cfg.get('shortcut_generate', '')})",
            keys=cfg.get("shortcut_generate") or None,
        )
    )
    buttons.append(
        editor.addButton(
            icon=ICON_SETTINGS,
            cmd="pronunciation_tts_settings",
            func=on_settings,
            tip=f"Aussprache: Felder und Akzent wählen ({cfg.get('shortcut_settings', '')})",
            keys=cfg.get("shortcut_settings") or None,
        )
    )


def setup() -> None:
    gui_hooks.editor_did_init_buttons.append(_add_buttons)
