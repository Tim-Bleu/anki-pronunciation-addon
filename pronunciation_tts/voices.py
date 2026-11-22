"""Catalogue of supported languages / accents.

Each voice maps to
  * a Google Translate language code + top-level domain (the TLD selects the
    regional accent, e.g. ``co.uk`` -> British English), and
  * a BCP-47 code for the Google Cloud Text-to-Speech API.

This module is pure Python and must not import aqt/anki.
"""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import current_language, tr


@dataclass(frozen=True)
class Voice:
    id: str  # stable id, stored in config (BCP-47 style)
    label_en: str  # shown in the UI
    label_de: str
    gt_lang: str  # Google Translate language code
    gt_tld: str  # Google Translate TLD -> accent
    cloud_code: str  # Google Cloud TTS languageCode

    @property
    def label(self) -> str:
        return self.label_de if current_language() == "de" else self.label_en


VOICES: tuple[Voice, ...] = (
    Voice("en-US", "English (American)", "Englisch (Amerikanisch)", "en", "com", "en-US"),
    Voice("en-GB", "English (British)", "Englisch (Britisch)", "en", "co.uk", "en-GB"),
    Voice("en-AU", "English (Australian)", "Englisch (Australisch)", "en", "com.au", "en-AU"),
    Voice("en-CA", "English (Canadian)", "Englisch (Kanadisch)", "en", "ca", "en-US"),
    Voice("en-IN", "English (Indian)", "Englisch (Indisch)", "en", "co.in", "en-IN"),
    Voice("en-IE", "English (Irish)", "Englisch (Irisch)", "en", "ie", "en-GB"),
    Voice("en-ZA", "English (South African)", "Englisch (Südafrikanisch)", "en", "co.za", "en-GB"),
    Voice("fr-FR", "French (France)", "Französisch (Frankreich)", "fr", "fr", "fr-FR"),
    Voice("fr-CA", "French (Canada)", "Französisch (Kanada)", "fr", "ca", "fr-CA"),
    Voice("es-ES", "Spanish (Spain)", "Spanisch (Spanien)", "es", "es", "es-ES"),
    Voice("es-MX", "Spanish (Mexico)", "Spanisch (Mexiko)", "es", "com.mx", "es-US"),
    Voice("pt-BR", "Portuguese (Brazil)", "Portugiesisch (Brasilien)", "pt", "com.br", "pt-BR"),
    Voice("pt-PT", "Portuguese (Portugal)", "Portugiesisch (Portugal)", "pt", "pt", "pt-PT"),
    Voice("de-DE", "German", "Deutsch", "de", "de", "de-DE"),
    Voice("it-IT", "Italian", "Italienisch", "it", "it", "it-IT"),
    Voice("nl-NL", "Dutch", "Niederländisch", "nl", "nl", "nl-NL"),
    Voice("sv-SE", "Swedish", "Schwedisch", "sv", "se", "sv-SE"),
    Voice("nb-NO", "Norwegian", "Norwegisch", "no", "no", "nb-NO"),
    Voice("da-DK", "Danish", "Dänisch", "da", "dk", "da-DK"),
    Voice("fi-FI", "Finnish", "Finnisch", "fi", "fi", "fi-FI"),
    Voice("pl-PL", "Polish", "Polnisch", "pl", "pl", "pl-PL"),
    Voice("cs-CZ", "Czech", "Tschechisch", "cs", "cz", "cs-CZ"),
    Voice("ru-RU", "Russian", "Russisch", "ru", "ru", "ru-RU"),
    Voice("uk-UA", "Ukrainian", "Ukrainisch", "uk", "com.ua", "uk-UA"),
    Voice("el-GR", "Greek", "Griechisch", "el", "gr", "el-GR"),
    Voice("tr-TR", "Turkish", "Türkisch", "tr", "com.tr", "tr-TR"),
    Voice("ar-XA", "Arabic", "Arabisch", "ar", "com", "ar-XA"),
    Voice("ja-JP", "Japanese", "Japanisch", "ja", "co.jp", "ja-JP"),
    Voice("ko-KR", "Korean", "Koreanisch", "ko", "co.kr", "ko-KR"),
    Voice("zh-CN", "Chinese (Mandarin, simplified)", "Chinesisch (Mandarin, vereinfacht)", "zh-CN", "com", "cmn-CN"),
    Voice("zh-TW", "Chinese (Mandarin, Taiwan)", "Chinesisch (Mandarin, Taiwan)", "zh-TW", "com.tw", "cmn-TW"),
)

_BY_ID = {v.id: v for v in VOICES}

DEFAULT_VOICE_ID = "en-GB"


def get_voice(voice_id: str | None) -> Voice:
    """Return the voice for ``voice_id`` or raise KeyError."""
    if voice_id not in _BY_ID:
        raise KeyError(tr("tts.unknown_voice", voice=voice_id))
    return _BY_ID[voice_id]


def is_known_voice(voice_id: str | None) -> bool:
    return voice_id in _BY_ID


def google_translate_hosts() -> frozenset[str]:
    """Exact host names the Google Translate provider may contact."""
    return frozenset(f"translate.google.{v.gt_tld}" for v in VOICES)
