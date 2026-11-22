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
from aqt.utils import askUser, showWarning, tooltip

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
    if s.source not in fields or not is_known_voice(s.voice):
        return None
    if s.placement not in core.PLACEMENTS:
        return None
    if s.placement == core.PLACEMENT_FIELD and s.target not in fields:
        return None
    if s.placement in core.CLOZE_PLACEMENTS and nt["type"] != MODEL_CLOZE:
        return None
    if s.cloze_text not in (core.CLOZE_TEXT_SENTENCE, core.CLOZE_TEXT_WORD):
        return None
    return s


def _default_settings(cfg: dict, fields, fronts, backs, is_cloze) -> NoteTypeSettings:
    source, target = core.default_fields(fields, fronts, backs, is_cloze)
    voice = cfg.get("default_voice", DEFAULT_VOICE_ID)
    if not is_known_voice(voice):
        voice = DEFAULT_VOICE_ID
    placement = core.PLACEMENT_CLOZE_FIELD if is_cloze else core.PLACEMENT_FIELD
    return NoteTypeSettings(source, target, voice, bool(cfg.get("slow", False)), placement)


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


def _ensure_cloze_audio_field(editor: Editor, note: Note) -> Note | None:
    """Make sure the note type has the per-cloze audio field and renders it with
    ``{{cloze-only:…}}`` on the back. Asks once before changing the note type.

    Returns the note to continue with (in add mode a fresh note object that has
    the new field), or None if the user declined.
    """
    field = core.CLOZE_AUDIO_FIELD
    nt = note.note_type()
    has_field = field in [f["name"] for f in nt["flds"]]
    has_template = core.cloze_only_on_back(field, [t["afmt"] for t in nt["tmpls"]])
    if has_field and has_template:
        return note
    if not askUser(tr("ed.setup_cloze_audio", nt=nt["name"], f=field), parent=editor.widget):
        return None
    # Adding a field is a schema change (Anki may ask for a full sync once).
    if not has_field and not mw.confirm_schema_modification():
        return None

    models = mw.col.models
    if not has_field:
        models.add_field(nt, models.new_field(field))
    for tmpl in nt["tmpls"]:
        tmpl["afmt"] = core.add_cloze_only(tmpl["afmt"], field)
    models.update_dict(nt)

    if editor.addMode or not note.id:
        fresh = mw.col.new_note(models.get(nt["id"]))
        for name, value in note.items():
            fresh[name] = value
        fresh.tags = list(note.tags)
        editor.set_note(fresh)
        return fresh
    note.load()
    editor.loadNoteKeepingFocus()
    return note


def _run(editor: Editor, note: Note, settings: NoteTypeSettings, cfg: dict) -> None:
    _fields, fronts, _backs, is_cloze, _nt = _templates(note)
    replace = bool(cfg.get("replace_existing_audio", True))
    source_html = note[settings.source]
    sentence = field_to_speech_text(source_html)

    if settings.placement in core.CLOZE_PLACEMENTS:
        if not is_cloze or not core.field_is_cloze_rendered(settings.source, fronts):
            showWarning(tr("ed.not_cloze_field", f=settings.source), parent=editor.widget)
            return
        answers = core.cloze_answers(source_html)
        if not answers:
            tooltip(tr("ed.no_cloze", f=settings.source), parent=editor.widget)
            return
        if settings.placement == core.PLACEMENT_CLOZE_FIELD:
            if core.field_on_front(core.CLOZE_AUDIO_FIELD, fronts):
                showWarning(tr("dlg.cloze_field_on_front", f=core.CLOZE_AUDIO_FIELD), parent=editor.widget)
                return
            ensured = _ensure_cloze_audio_field(editor, note)
            if ensured is None:
                return
            note = ensured
        # Rule: several cloze numbers = several foreign words -> each deletion gets
        # only its own word, regardless of the "whole sentence" setting.
        cloze_text = core.effective_cloze_text(source_html, settings.cloze_text)
        texts = [t for _, t in answers] if cloze_text == core.CLOZE_TEXT_WORD else [sentence]
    else:
        cloze_text = settings.cloze_text
        if core.field_on_front(settings.target, fronts):
            showWarning(tr("ed.target_on_front", f=settings.target), parent=editor.widget)
            return
        texts = [sentence]

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

    def update(target_note: Note, stored: dict[str, str]) -> None:
        if settings.placement == core.PLACEMENT_CLOZE_FIELD:
            # Our tags from the "into the cloze text" mode would play for every cloze.
            if replace:
                target_note[settings.source] = core.strip_own_sound_tags(target_note[settings.source])
            target_note[core.CLOZE_AUDIO_FIELD] = core.build_cloze_audio(
                target_note[settings.source], cloze_text, stored, sentence
            )
        elif settings.placement == core.PLACEMENT_CLOZE:
            current = target_note[settings.source]
            if cloze_text == core.CLOZE_TEXT_WORD:
                pick = lambda _n, text, _f: stored.get(text)  # noqa: E731
            else:
                pick = lambda _n, _t, first: stored[sentence] if first else None  # noqa: E731
            target_note[settings.source] = core.insert_sound_in_clozes(current, pick, replace)
        else:
            target_note[settings.target] = core.insert_sound_tag(
                target_note[settings.target], stored[texts[0]], replace
            )

    def on_success(stored: dict[str, str]) -> None:
        _apply(editor, note, lambda n: update(n, stored))
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


def _apply(editor: Editor, note: Note, update) -> None:
    """Apply ``update(note)`` to the note and save/refresh appropriately."""
    if editor.note is not note:
        # The user switched to another note while downloading.
        if not note.id:
            return
        note = mw.col.get_note(note.id)
        update(note)
        update_note(parent=editor.widget, note=note).run_in_background()
        return

    update(note)
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
