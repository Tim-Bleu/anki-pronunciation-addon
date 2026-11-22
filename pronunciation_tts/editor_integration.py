"""Editor buttons, shortcuts and the background download."""

from __future__ import annotations

import json
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
from aqt.utils import showWarning, tooltip

from . import core
from .dialog import NoteTypeSettings, SettingsDialog
from .i18n import resolve_language, set_language, tr
from .providers import TTSError, make_provider
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
            placement=str(raw.get("placement", core.PLACEMENT_FIELD)),
            cloze_text=str(raw.get("cloze_text", core.CLOZE_TEXT_SENTENCE)),
        )
    except (KeyError, TypeError):
        return None
    if s.source not in fields or s.target not in fields or not is_known_voice(s.voice):
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
    return NoteTypeSettings(source, target, voice, bool(cfg.get("slow", False)))


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
    cfg["note_types"][str(nt["id"])] = asdict(settings)
    write_config(cfg)
    _run(editor, note, settings, cfg)


def _run(editor: Editor, note: Note, settings: NoteTypeSettings, cfg: dict) -> None:
    _fields, fronts, _backs, is_cloze, _nt = _templates(note)
    replace = bool(cfg.get("replace_existing_audio", True))
    source_html = note[settings.source]

    if settings.placement == core.PLACEMENT_CLOZE:
        if not is_cloze or not core.field_is_cloze_rendered(settings.source, fronts):
            showWarning(tr("ed.not_cloze_field", f=settings.source), parent=editor.widget)
            return
        answers = core.cloze_answers(source_html)
        if not answers:
            tooltip(tr("ed.no_cloze", f=settings.source), parent=editor.widget)
            return
        # Rule: several cloze numbers = several foreign words -> each deletion gets
        # only its own word, regardless of the "whole sentence" setting.
        cloze_text = core.effective_cloze_text(source_html, settings.cloze_text)
        if cloze_text == core.CLOZE_TEXT_WORD:
            texts = [t for _, t in answers if t]
        else:
            texts = [field_to_speech_text(source_html)]
    else:
        cloze_text = settings.cloze_text
        if core.field_on_front(settings.target, fronts):
            showWarning(tr("ed.target_on_front", f=settings.target), parent=editor.widget)
            return
        texts = [field_to_speech_text(source_html)]

    texts = list(dict.fromkeys(t for t in texts if t))  # unique, keep order
    if not texts:
        tooltip(tr("ed.empty", f=settings.source), parent=editor.widget)
        return

    try:
        voice = get_voice(settings.voice)
        provider = make_provider(cfg)
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
            if cloze_text == core.CLOZE_TEXT_WORD:
                return core.insert_sound_in_clozes(current, lambda _n, text, _f: stored.get(text), replace)
            sentence = stored[texts[0]]
            return core.insert_sound_in_clozes(current, lambda _n, _t, first: sentence if first else None, replace)
        return core.insert_sound_tag(current, stored[texts[0]], replace)

    def on_success(stored: dict[str, str]) -> None:
        field = settings.source if settings.placement == core.PLACEMENT_CLOZE else settings.target
        _apply(editor, note, field, lambda current: transform(current, stored))
        if cfg.get("play_after_insert", True):
            av_player.play_tags([SoundOrVideoTag(filename=f) for f in stored.values()])
        tooltip(tr("ed.done"), parent=editor.widget)

    def on_failure(exc: Exception) -> None:
        showWarning(tr("ed.failed", err=exc), parent=editor.widget)

    (
        QueryOp(parent=editor.widget, op=op, success=on_success)
        .failure(on_failure)
        .with_progress(tr("ed.progress"))
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
            tip=tr("ed.tip_generate", keys=cfg.get("shortcut_generate", "")),
            keys=cfg.get("shortcut_generate") or None,
        )
    )
    buttons.append(
        editor.addButton(
            icon=ICON_SETTINGS,
            cmd="pronunciation_tts_settings",
            func=on_settings,
            tip=tr("ed.tip_settings", keys=cfg.get("shortcut_settings", "")),
            keys=cfg.get("shortcut_settings") or None,
        )
    )


def _sync_addon_name() -> None:
    """Show the (English) name from manifest.json in Anki's add-on list, also for
    installs made before the rename. Anki itself only reads it on (re)install."""
    try:
        with open(os.path.join(ADDON_DIR, "manifest.json"), encoding="utf8") as f:
            name = json.load(f).get("name")
        meta = mw.addonManager.addonMeta(ADDON_MODULE)
        if isinstance(name, str) and name and meta.get("name") != name:
            meta["name"] = name
            mw.addonManager.writeAddonMeta(ADDON_MODULE, meta)
    except Exception:  # never break start-up over a display name
        pass


def setup() -> None:
    _sync_addon_name()
    try:
        from anki.lang import current_lang
    except ImportError:  # pragma: no cover
        current_lang = "en"
    set_language(resolve_language(get_config().get("language", "auto"), current_lang))
    gui_hooks.editor_did_init_buttons.append(_add_buttons)
