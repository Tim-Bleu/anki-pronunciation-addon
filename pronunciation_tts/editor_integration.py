"""Editor buttons, shortcuts and the background download."""

from __future__ import annotations

import os
from dataclasses import asdict

from anki.consts import MODEL_CLOZE
from anki.notes import Note
from aqt import gui_hooks, mw
from aqt.editor import Editor
from aqt.operations import QueryOp
from aqt.operations.note import update_note
from aqt.sound import av_player
from aqt.utils import showWarning, tooltip

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
        )
    except (KeyError, TypeError):
        return None
    if s.source not in fields or s.target not in fields or not is_known_voice(s.voice):
        return None
    if s.provider not in PROVIDER_IDS:
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
    dlg = SettingsDialog(editor.widget, fields, fronts, backs, initial, nt["name"])
    if not dlg.exec():
        return
    settings = dlg.result_settings()
    if dlg.remember.isChecked():
        cfg["note_types"][str(nt["id"])] = asdict(settings)
        write_config(cfg)
    _run(editor, note, settings, cfg)


def _run(editor: Editor, note: Note, settings: NoteTypeSettings, cfg: dict) -> None:
    _fields, fronts, _backs, _is_cloze, _nt = _templates(note)
    if core.field_on_front(settings.target, fronts):
        showWarning(
            f"Das Zielfeld „{settings.target}“ ist auf der Vorderseite sichtbar. "
            "Das Audio würde vor dem Aufdecken abgespielt. Bitte ein anderes Zielfeld wählen "
            "(zweiter Lautsprecher-Knopf).",
            parent=editor.widget,
        )
        return

    text = field_to_speech_text(note[settings.source])
    if not text:
        tooltip(f"Das Feld „{settings.source}“ ist leer.", parent=editor.widget)
        return

    try:
        voice = get_voice(settings.voice)
        provider = make_provider({**cfg, "provider": settings.provider})
    except (KeyError, TTSError) as e:
        showWarning(str(e), parent=editor.widget)
        return

    fname = core.media_filename(provider.id, voice.id, text, settings.slow)

    def op(col) -> str:
        if col.media.have(fname):
            return fname  # cached: same text, voice and speed
        data = provider.synthesize(text, voice, slow=settings.slow)
        return col.media.write_data(fname, data)

    def on_success(stored_name: str) -> None:
        _apply(editor, note, settings.target, stored_name, bool(cfg.get("replace_existing_audio", True)))
        if cfg.get("play_after_insert", True):
            av_player.play_file(stored_name)
        tooltip("Aussprache eingefügt.", parent=editor.widget)

    def on_failure(exc: Exception) -> None:
        showWarning(f"Aussprache konnte nicht erstellt werden:\n\n{exc}", parent=editor.widget)

    (
        QueryOp(parent=editor.widget, op=op, success=on_success)
        .failure(on_failure)
        .with_progress("Aussprache wird sicher heruntergeladen …")
        .run_in_background()
    )


def _apply(editor: Editor, note: Note, target: str, fname: str, replace: bool) -> None:
    if editor.note is not note:
        # The user switched to another note while downloading.
        if not note.id:
            return
        note = mw.col.get_note(note.id)
        note[target] = core.insert_sound_tag(note[target], fname, replace)
        update_note(parent=editor.widget, note=note).run_in_background()
        return

    note[target] = core.insert_sound_tag(note[target], fname, replace)
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
