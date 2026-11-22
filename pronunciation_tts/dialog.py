"""Settings dialog shown in the editor (source/target field, voice)."""

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
from .providers import GoogleCloudProvider, GoogleTranslateProvider
from .voices import VOICES


@dataclass
class NoteTypeSettings:
    source: str
    target: str
    voice: str
    slow: bool = False
    provider: str = GoogleTranslateProvider.id


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        field_names: list[str],
        front_templates: list[str],
        back_templates: list[str],
        initial: NoteTypeSettings,
        note_type_name: str,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aussprache einfügen")
        self._front = front_templates
        self._back = back_templates

        self.source = QComboBox()
        self.source.addItems(field_names)
        self.target = QComboBox()
        self.target.addItems(field_names)
        self.voice = QComboBox()
        for v in VOICES:
            self.voice.addItem(v.label, v.id)
        self.provider = QComboBox()
        for pid, label in (
            (GoogleTranslateProvider.id, GoogleTranslateProvider.label),
            (GoogleCloudProvider.id, GoogleCloudProvider.label),
        ):
            self.provider.addItem(label, pid)
        self.slow = QCheckBox("Langsam sprechen")
        self.remember = QCheckBox(f"Für Notiztyp „{note_type_name}“ merken (nächstes Mal ohne Nachfrage)")
        self.remember.setChecked(True)
        self.warning = QLabel()
        self.warning.setWordWrap(True)

        _select(self.source, initial.source)
        _select(self.target, initial.target)
        _select_data(self.voice, initial.voice)
        _select_data(self.provider, initial.provider)
        self.slow.setChecked(initial.slow)

        form = QFormLayout()
        form.addRow("Text vorlesen aus Feld:", self.source)
        form.addRow("Audio einfügen in Feld:", self.target)
        form.addRow("Sprache / Akzent:", self.voice)
        form.addRow("Dienst:", self.provider)
        form.addRow("", self.slow)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aussprache einfügen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addWidget(self.remember)
        layout.addWidget(self.buttons)

        self.target.currentIndexChanged.connect(self._update_warning)
        self._update_warning()

    def _update_warning(self) -> None:
        target = self.target.currentText()
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if core.field_on_front(target, self._front):
            self.warning.setText(
                "⚠ Das Feld „%s“ wird auf der <b>Vorderseite</b> angezeigt – das Audio würde "
                "die Lösung verraten. Bitte ein Feld wählen, das nur auf der Rückseite steht "
                "(z. B. „Back Extra“ oder ein eigenes Feld „Audio“)." % target
            )
            ok_button.setEnabled(False)
        elif not core.field_on_back(target, self._back):
            self.warning.setText(
                "⚠ Das Feld „%s“ kommt in keiner Rückseiten-Vorlage vor – das Audio wäre "
                "beim Lernen nicht zu hören. Füge <code>{{%s}}</code> in die Rückseite der "
                "Kartenvorlage ein." % (target, target)
            )
            ok_button.setEnabled(True)
        else:
            self.warning.setText("✔ Das Audio wird erst nach dem Aufdecken der Karte abgespielt.")
            ok_button.setEnabled(True)

    def result_settings(self) -> NoteTypeSettings:
        return NoteTypeSettings(
            source=self.source.currentText(),
            target=self.target.currentText(),
            voice=self.voice.currentData(),
            slow=self.slow.isChecked(),
            provider=self.provider.currentData(),
        )


def _select(combo: QComboBox, text: str) -> None:
    idx = combo.findText(text)
    if idx >= 0:
        combo.setCurrentIndex(idx)


def _select_data(combo: QComboBox, data: str) -> None:
    idx = combo.findData(data)
    if idx >= 0:
        combo.setCurrentIndex(idx)
