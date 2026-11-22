"""Tiny translation layer (German / English). Pure Python, no aqt/anki imports.

The language is chosen once at start-up (``set_language``): ``"auto"`` follows
Anki's UI language (German if it starts with ``de``, otherwise English).
"""

from __future__ import annotations

SUPPORTED = ("en", "de")
_lang = "en"

MESSAGES: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- net
    "net.https_only": {
        "en": "Only HTTPS connections are allowed.",
        "de": "Nur HTTPS-Verbindungen sind erlaubt.",
    },
    "net.no_credentials": {
        "en": "Credentials in URLs are not allowed.",
        "de": "Zugangsdaten in URLs sind nicht erlaubt.",
    },
    "net.host_not_allowed": {
        "en": "Host {host!r} is not on the allow-list.",
        "de": "Host {host!r} ist nicht auf der Erlaubt-Liste.",
    },
    "net.redirect": {
        "en": "The server sent a redirect (HTTP {code}); for security reasons it is not followed.",
        "de": "Der Server hat eine Weiterleitung geschickt (HTTP {code}); aus Sicherheitsgründen wird ihr nicht gefolgt.",
    },
    "net.http_status": {
        "en": "The server responded with HTTP {code}.",
        "de": "Der Server antwortete mit HTTP {code}.",
    },
    "net.tls": {
        "en": "Secure connection failed (TLS): {reason}",
        "de": "Sichere Verbindung fehlgeschlagen (TLS): {reason}",
    },
    "net.connect": {
        "en": "Connection failed: {reason}",
        "de": "Verbindung fehlgeschlagen: {reason}",
    },
    "net.timeout": {
        "en": "Timed out while downloading.",
        "de": "Zeitüberschreitung beim Herunterladen.",
    },
    "net.network": {
        "en": "Network error: {reason}",
        "de": "Netzwerkfehler: {reason}",
    },
    "net.too_big": {
        "en": "The server's response is too large.",
        "de": "Die Antwort des Servers ist zu groß.",
    },
    # ---------------------------------------------------------------- audio
    "audio.bad_type": {
        "en": "Audio data has an invalid type.",
        "de": "Audio-Daten haben einen ungültigen Typ.",
    },
    "audio.too_small": {
        "en": "The downloaded audio file is empty or too small.",
        "de": "Die heruntergeladene Audiodatei ist leer oder zu klein.",
    },
    "audio.too_big": {
        "en": "The downloaded audio file is too large.",
        "de": "Die heruntergeladene Audiodatei ist zu groß.",
    },
    "audio.not_mp3": {
        "en": "The downloaded file is not a valid MP3 file.",
        "de": "Die heruntergeladene Datei ist keine gültige MP3-Datei.",
    },
    # ---------------------------------------------------------------- providers
    "tts.no_text": {"en": "There is no text to read aloud.", "de": "Kein Text zum Vorlesen vorhanden."},
    "tts.too_long": {
        "en": "The text is too long (max. {max} characters).",
        "de": "Der Text ist zu lang (max. {max} Zeichen).",
    },
    "tts.bad_voice": {"en": "Invalid voice.", "de": "Ungültige Stimme."},
    "tts.unknown_voice": {"en": "Unknown voice: {voice!r}", "de": "Unbekannte Stimme: {voice!r}"},
    "tts.gt_status": {
        "en": "Google Translate responded with HTTP {code}.",
        "de": "Google Translate antwortete mit HTTP {code}.",
    },
    "tts.gt_no_audio": {
        "en": "Google Translate did not return any audio.",
        "de": "Google Translate hat keine Audiodaten geliefert.",
    },
    "tts.cloud_no_key": {
        "en": "Google Cloud TTS needs a valid API key (Tools → Add-ons → Config).",
        "de": "Für Google Cloud TTS fehlt ein gültiger API-Schlüssel (Extras → Add-ons → Konfiguration).",
    },
    "tts.cloud_bad_voice_name": {
        "en": "Invalid voice name for Google Cloud TTS.",
        "de": "Ungültiger Stimmenname für Google Cloud TTS.",
    },
    "tts.cloud_unexpected": {
        "en": "Unexpected response from Google Cloud (HTTP {code}).",
        "de": "Unerwartete Antwort von Google Cloud (HTTP {code}).",
    },
    "tts.cloud_error": {
        "en": "Google Cloud TTS error (HTTP {code}): {msg}",
        "de": "Google Cloud TTS-Fehler (HTTP {code}): {msg}",
    },
    "tts.cloud_no_audio": {
        "en": "Google Cloud TTS did not return any audio.",
        "de": "Google Cloud TTS hat keine Audiodaten geliefert.",
    },
    "tts.corrupt": {"en": "The audio data is corrupt.", "de": "Audiodaten sind beschädigt."},
    "tts.unknown_provider": {"en": "Unknown service: {pid!r}", "de": "Unbekannter Anbieter: {pid!r}"},
    # ---------------------------------------------------------------- dialog
    "dlg.title": {"en": "Insert pronunciation", "de": "Aussprache einfügen"},
    "dlg.source": {"en": "Read text from field:", "de": "Text vorlesen aus Feld:"},
    "dlg.placement": {"en": "Insert audio:", "de": "Audio einfügen:"},
    "dlg.placement_field": {"en": "Into a back-side field", "de": "In ein Feld der Rückseite"},
    "dlg.placement_cloze": {
        "en": "Directly into the cloze",
        "de": "Direkt in die Lücke (im Lückentext)",
    },
    "dlg.target": {"en": "Insert audio into field:", "de": "Audio einfügen in Feld:"},
    "dlg.cloze_text": {"en": "Read aloud:", "de": "Vorlesen:"},
    "dlg.cloze_sentence": {"en": "Whole sentence", "de": "Ganzen Satz"},
    "dlg.cloze_word": {"en": "Cloze word only", "de": "Nur das Lückenwort"},
    "dlg.voice": {"en": "Language / accent:", "de": "Sprache / Akzent:"},
    "dlg.slow": {"en": "Speak slowly", "de": "Langsam sprechen"},
    "dlg.ok": {"en": "Insert pronunciation", "de": "Aussprache einfügen"},
    "dlg.remember_hint": {
        "en": "These settings are remembered for the note type “{name}”. "
        "Change them later with the second speaker button.",
        "de": "Die Einstellungen werden für den Notiztyp „{name}“ gemerkt. "
        "Ändern kannst du sie später über den zweiten Lautsprecher-Knopf.",
    },
    "dlg.not_cloze_field": {
        "en": "⚠ The field “{f}” is not a cloze field (<code>{{{{cloze:{f}}}}}</code>). "
        "Please choose the field that contains the clozes.",
        "de": "⚠ Das Feld „{f}“ ist kein Lückentext-Feld (<code>{{{{cloze:{f}}}}}</code>). "
        "Bitte das Feld mit den Lücken wählen.",
    },
    "dlg.cloze_ok": {
        "en": "✔ The audio sits inside the cloze and only plays after it is revealed.<br>"
        "<small>With several clozes (c1, c2 …) each cloze gets only its own word. On the card "
        "for c1, the visible cloze c2 is read aloud on the front – this never reveals the "
        "answer you are asked for.</small>",
        "de": "✔ Das Audio steht in der Lücke und wird erst nach dem Aufdecken abgespielt.<br>"
        "<small>Bei mehreren Lücken (c1, c2 …) bekommt jede Lücke nur ihr eigenes Wort. Auf der "
        "Karte für c1 wird die sichtbare Lücke c2 schon vorne vorgelesen – die gesuchte Lösung "
        "verrät das nie.</small>",
    },
    "dlg.on_front": {
        "en": "⚠ The field “{f}” is shown on the <b>front</b> – the audio would give the answer "
        "away. Please choose a field that is only on the back (e.g. “Back Extra” or your own "
        "“Audio” field){extra}.",
        "de": "⚠ Das Feld „{f}“ wird auf der <b>Vorderseite</b> angezeigt – das Audio würde "
        "die Lösung verraten. Bitte ein Feld wählen, das nur auf der Rückseite steht "
        "(z. B. „Back Extra“ oder ein eigenes Feld „Audio“){extra}.",
    },
    "dlg.on_front_cloze_extra": {
        "en": " or “Directly into the cloze”",
        "de": " oder „Direkt in die Lücke“",
    },
    "dlg.not_on_back": {
        "en": "⚠ The field “{f}” is not used on any back template – you would never hear the "
        "audio while studying. Add <code>{{{{{f}}}}}</code> to the back of the card template.",
        "de": "⚠ Das Feld „{f}“ kommt in keiner Rückseiten-Vorlage vor – das Audio wäre "
        "beim Lernen nicht zu hören. Füge <code>{{{{{f}}}}}</code> in die Rückseite der "
        "Kartenvorlage ein.",
    },
    "dlg.back_ok": {
        "en": "✔ The audio only plays after the card is revealed.",
        "de": "✔ Das Audio wird erst nach dem Aufdecken der Karte abgespielt.",
    },
    # ---------------------------------------------------------------- editor
    "ed.tip_generate": {"en": "Insert pronunciation ({keys})", "de": "Aussprache einfügen ({keys})"},
    "ed.tip_settings": {
        "en": "Pronunciation: choose fields and accent ({keys})",
        "de": "Aussprache: Felder und Akzent wählen ({keys})",
    },
    "ed.not_cloze_field": {
        "en": "“{f}” is not a cloze field. Please choose another field or insert location "
        "with the second speaker button.",
        "de": "„{f}“ ist kein Lückentext-Feld. Bitte über den zweiten Lautsprecher-Knopf ein "
        "anderes Feld oder einen anderen Einfügeort wählen.",
    },
    "ed.no_cloze": {
        "en": "No cloze ({{{{c1::…}}}}) found in the field “{f}”.",
        "de": "Im Feld „{f}“ wurde keine Lücke ({{{{c1::…}}}}) gefunden.",
    },
    "ed.target_on_front": {
        "en": "The target field “{f}” is visible on the front. The audio would play before the "
        "card is revealed. Please choose another target field (second speaker button).",
        "de": "Das Zielfeld „{f}“ ist auf der Vorderseite sichtbar. Das Audio würde vor dem "
        "Aufdecken abgespielt. Bitte ein anderes Zielfeld wählen (zweiter Lautsprecher-Knopf).",
    },
    "ed.empty": {"en": "The field “{f}” is empty.", "de": "Das Feld „{f}“ ist leer."},
    "ed.done": {"en": "Pronunciation inserted.", "de": "Aussprache eingefügt."},
    "ed.failed": {
        "en": "Could not create the pronunciation:\n\n{err}",
        "de": "Aussprache konnte nicht erstellt werden:\n\n{err}",
    },
    "ed.progress": {
        "en": "Securely downloading pronunciation …",
        "de": "Aussprache wird sicher heruntergeladen …",
    },
}


def resolve_language(setting: str | None, anki_lang: str | None) -> str:
    """``setting`` from config ("auto"/"en"/"de"), ``anki_lang`` like "de_DE"."""
    setting = (setting or "auto").lower()
    if setting in SUPPORTED:
        return setting
    return "de" if (anki_lang or "").lower().startswith("de") else "en"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in SUPPORTED else "en"


def current_language() -> str:
    return _lang


def tr(key: str, **kwargs) -> str:
    entry = MESSAGES[key]
    text = entry.get(_lang) or entry["en"]
    return text.format(**kwargs) if kwargs else text
