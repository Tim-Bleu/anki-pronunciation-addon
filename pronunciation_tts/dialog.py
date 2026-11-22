"""Settings dialog shown in the editor (source/target field, voice, placement)."""

from __future__ import annotations

from dataclasses import dataclass

from aqt.qt import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from . import core
from .i18n import tr
from .voices import VOICES


@dataclass
class NoteTypeSettings:
    source: str
    target: str
    voice: str
    slow: bool = False
    # "field": append to target field; "cloze": put audio inside the cloze deletion(s)
    placement: str = core.PLACEMENT_FIELD
    # only for placement "cloze": speak the whole sentence or only the cloze answer
    cloze_text: str = core.CLOZE_TEXT_SENTENCE


class SettingsDialog(QDialog):
    """Asks for fields, placement and accent. Settings are always remembered
    per note type by the caller; the service (provider) lives in the config."""

    def __init__(
        self,
        parent: QWidget | None,
        field_names: list[str],
        front_templates: list[str],
        back_templates: list[str],
        initial: NoteTypeSettings,
        note_type_name: str,
        is_cloze: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.title"))
        self._front = front_templates
        self._back = back_templates
        self._is_cloze = is_cloze

        self.source = QComboBox()
        self.source.addItems(field_names)
        self.placement = QComboBox()
        self.placement.addItem(tr("dlg.placement_field"), core.PLACEMENT_FIELD)
        if is_cloze:
            self.placement.addItem(tr("dlg.placement_cloze"), core.PLACEMENT_CLOZE)
        self.target = QComboBox()
        self.target.addItems(field_names)
        self.cloze_text = QComboBox()
        self.cloze_text.addItem(tr("dlg.cloze_sentence"), core.CLOZE_TEXT_SENTENCE)
        self.cloze_text.addItem(tr("dlg.cloze_word"), core.CLOZE_TEXT_WORD)
        self.voice = QComboBox()
        for v in sorted(VOICES, key=lambda v: v.label.casefold()):
            self.voice.addItem(v.label, v.id)
        self.slow = QCheckBox(tr("dlg.slow"))
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        hint = QLabel(f"<small>{tr('dlg.remember_hint', name=note_type_name)}</small>")
        hint.setWordWrap(True)

        _select(self.source, initial.source)
        _select(self.target, initial.target)
        _select_data(self.placement, initial.placement)
        _select_data(self.cloze_text, initial.cloze_text)
        _select_data(self.voice, initial.voice)
        self.slow.setChecked(initial.slow)

        form = QFormLayout()
        form.addRow(tr("dlg.source"), self.source)
        self._placement_label = QLabel(tr("dlg.placement"))
        form.addRow(self._placement_label, self.placement)
        self._target_label = QLabel(tr("dlg.target"))
        form.addRow(self._target_label, self.target)
        self._cloze_text_label = QLabel(tr("dlg.cloze_text"))
        form.addRow(self._cloze_text_label, self.cloze_text)
        form.addRow(tr("dlg.voice"), self.voice)
        form.addRow("", self.slow)

        # Only cloze note types have a choice of placement.
        self._placement_label.setVisible(is_cloze)
        self.placement.setVisible(is_cloze)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("dlg.ok"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addWidget(hint)
        layout.addWidget(self.buttons)

        self.target.currentIndexChanged.connect(self._update)
        self.source.currentIndexChanged.connect(self._update)
        self.placement.currentIndexChanged.connect(self._update)
        self._update()

    def _in_cloze(self) -> bool:
        return self.placement.currentData() == core.PLACEMENT_CLOZE

    def _update(self) -> None:
        in_cloze = self._in_cloze()
        for w in (self.target, self._target_label):
            w.setVisible(not in_cloze)
        for w in (self.cloze_text, self._cloze_text_label):
            w.setVisible(in_cloze)
        ok, text = self._check()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
        self.warning.setText(text)
        self.adjustSize()

    def _check(self) -> tuple[bool, str]:
        if self._in_cloze():
            source = self.source.currentText()
            if not core.field_is_cloze_rendered(source, self._front):
                return False, tr("dlg.not_cloze_field", f=source)
            return True, tr("dlg.cloze_ok")
        target = self.target.currentText()
        if core.field_on_front(target, self._front):
            extra = tr("dlg.on_front_cloze_extra") if self._is_cloze else ""
            return False, tr("dlg.on_front", f=target, extra=extra)
        if not core.field_on_back(target, self._back):
            return True, tr("dlg.not_on_back", f=target)
        return True, tr("dlg.back_ok")

    def result_settings(self) -> NoteTypeSettings:
        return NoteTypeSettings(
            source=self.source.currentText(),
            target=self.target.currentText(),
            voice=self.voice.currentData(),
            slow=self.slow.isChecked(),
            placement=self.placement.currentData(),
            cloze_text=self.cloze_text.currentData(),
        )


def _select(combo: QComboBox, text: str) -> None:
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _select_data(combo: QComboBox, data: str) -> None:
    idx = combo.findData(data)
    if idx >= 0:
        combo.setCurrentIndex(idx)
