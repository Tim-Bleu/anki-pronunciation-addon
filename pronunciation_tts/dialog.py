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
from .providers import GoogleCloudProvider, GoogleTranslateProvider
from .voices import VOICES


@dataclass
class NoteTypeSettings:
    source: str
    target: str
    voice: str
    slow: bool = False
    provider: str = GoogleTranslateProvider.id
    # "field": append to target field; "cloze": put audio inside the cloze deletion(s)
    placement: str = core.PLACEMENT_FIELD
    # only for placement "cloze": speak the whole sentence or only the cloze answer
    cloze_text: str = core.CLOZE_TEXT_SENTENCE


class SettingsDialog(QDialog):
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
        self.setWindowTitle("Aussprache einfügen")
        self._front = front_templates
        self._back = back_templates
        self._is_cloze = is_cloze

        self.source = QComboBox()
        self.source.addItems(field_names)
        self.placement = QComboBox()
        self.placement.addItem("In ein Feld der Rückseite", core.PLACEMENT_FIELD)
        if is_cloze:
            self.placement.addItem("Direkt in die Lücke (im Lückentext)", core.PLACEMENT_CLOZE)
        self.target = QComboBox()
        self.target.addItems(field_names)
        self.cloze_text = QComboBox()
        self.cloze_text.addItem("Ganzen Satz vorlesen", core.CLOZE_TEXT_SENTENCE)
        self.cloze_text.addItem("Nur das Lückenwort vorlesen", core.CLOZE_TEXT_WORD)
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
        _select_data(self.placement, initial.placement)
        _select_data(self.cloze_text, initial.cloze_text)
        _select_data(self.voice, initial.voice)
        _select_data(self.provider, initial.provider)
        self.slow.setChecked(initial.slow)

        form = QFormLayout()
        form.addRow("Text vorlesen aus Feld:", self.source)
        form.addRow("Audio einfügen:", self.placement)
        self._target_label = QLabel("Audio einfügen in Feld:")
        form.addRow(self._target_label, self.target)
        self._cloze_text_label = QLabel("Vorlesen:")
        form.addRow(self._cloze_text_label, self.cloze_text)
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
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok, text = self._check()
        ok_button.setEnabled(ok)
        self.warning.setText(text)
        self.adjustSize()

    def _check(self) -> tuple[bool, str]:
        if self._in_cloze():
            source = self.source.currentText()
            if not core.field_is_cloze_rendered(source, self._front):
                return False, (
                    "⚠ Das Feld „%s“ ist kein Lückentext-Feld (<code>{{cloze:%s}}</code>). "
                    "Bitte das Feld mit den Lücken wählen." % (source, source)
                )
            return True, (
                "✔ Das Audio steht in der Lücke und wird erst nach dem Aufdecken abgespielt.<br>"
                "<small>Hinweis: Hat eine Notiz mehrere Lücken-Nummern (c1, c2 …), ist auf der "
                "Karte c1 die Lücke c2 sichtbar – deren Audio wäre dort schon auf der Vorderseite "
                "zu hören. Dafür besser „In ein Feld der Rückseite“ wählen.</small>"
            )
        target = self.target.currentText()
        if core.field_on_front(target, self._front):
            return False, (
                "⚠ Das Feld „%s“ wird auf der <b>Vorderseite</b> angezeigt – das Audio würde "
                "die Lösung verraten. Bitte ein Feld wählen, das nur auf der Rückseite steht "
                "(z. B. „Back Extra“ oder ein eigenes Feld „Audio“)%s."
                % (target, " oder „Direkt in die Lücke“" if self._is_cloze else "")
            )
        if not core.field_on_back(target, self._back):
            return True, (
                "⚠ Das Feld „%s“ kommt in keiner Rückseiten-Vorlage vor – das Audio wäre "
                "beim Lernen nicht zu hören. Füge <code>{{%s}}</code> in die Rückseite der "
                "Kartenvorlage ein." % (target, target)
            )
        return True, "✔ Das Audio wird erst nach dem Aufdecken der Karte abgespielt."

    def result_settings(self) -> NoteTypeSettings:
        return NoteTypeSettings(
            source=self.source.currentText(),
            target=self.target.currentText(),
            voice=self.voice.currentData(),
            slow=self.slow.isChecked(),
            provider=self.provider.currentData(),
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
