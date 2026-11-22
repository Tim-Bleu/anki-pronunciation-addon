"""Catalogue of supported languages / accents.

Each voice maps to
  * a Google Translate language code + top-level domain (the TLD selects the
    regional accent, e.g. ``co.uk`` -> British English), and
  * a BCP-47 code for the Google Cloud Text-to-Speech API.

This module is pure Python and must not import aqt/anki.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Voice:
    id: str  # stable id, stored in config (BCP-47 style)
    label: str  # shown in the UI
    gt_lang: str  # Google Translate language code
    gt_tld: str  # Google Translate TLD -> accent
    cloud_code: str  # Google Cloud TTS languageCode


VOICES: tuple[Voice, ...] = (
    Voice("en-US", "Englisch (Amerikanisch)", "en", "com", "en-US"),
    Voice("en-GB", "Englisch (Britisch)", "en", "co.uk", "en-GB"),
    Voice("en-AU", "Englisch (Australisch)", "en", "com.au", "en-AU"),
    Voice("en-CA", "Englisch (Kanadisch)", "en", "ca", "en-US"),
    Voice("en-IN", "Englisch (Indisch)", "en", "co.in", "en-IN"),
    Voice("en-IE", "Englisch (Irisch)", "en", "ie", "en-GB"),
    Voice("en-ZA", "Englisch (Südafrikanisch)", "en", "co.za", "en-GB"),
    Voice("fr-FR", "Französisch (Frankreich)", "fr", "fr", "fr-FR"),
    Voice("fr-CA", "Französisch (Kanada)", "fr", "ca", "fr-CA"),
    Voice("es-ES", "Spanisch (Spanien)", "es", "es", "es-ES"),
    Voice("es-MX", "Spanisch (Mexiko)", "es", "com.mx", "es-US"),
    Voice("pt-BR", "Portugiesisch (Brasilien)", "pt", "com.br", "pt-BR"),
    Voice("pt-PT", "Portugiesisch (Portugal)", "pt", "pt", "pt-PT"),
    Voice("de-DE", "Deutsch", "de", "de", "de-DE"),
    Voice("it-IT", "Italienisch", "it", "it", "it-IT"),
    Voice("nl-NL", "Niederländisch", "nl", "nl", "nl-NL"),
    Voice("sv-SE", "Schwedisch", "sv", "se", "sv-SE"),
    Voice("nb-NO", "Norwegisch", "no", "no", "nb-NO"),
    Voice("da-DK", "Dänisch", "da", "dk", "da-DK"),
    Voice("fi-FI", "Finnisch", "fi", "fi", "fi-FI"),
    Voice("pl-PL", "Polnisch", "pl", "pl", "pl-PL"),
    Voice("cs-CZ", "Tschechisch", "cs", "cz", "cs-CZ"),
    Voice("ru-RU", "Russisch", "ru", "ru", "ru-RU"),
    Voice("uk-UA", "Ukrainisch", "uk", "com.ua", "uk-UA"),
    Voice("el-GR", "Griechisch", "el", "gr", "el-GR"),
    Voice("tr-TR", "Türkisch", "tr", "com.tr", "tr-TR"),
    Voice("ar-XA", "Arabisch", "ar", "com", "ar-XA"),
    Voice("ja-JP", "Japanisch", "ja", "co.jp", "ja-JP"),
    Voice("ko-KR", "Koreanisch", "ko", "co.kr", "ko-KR"),
    Voice("zh-CN", "Chinesisch (Mandarin, vereinfacht)", "zh-CN", "com", "cmn-CN"),
    Voice("zh-TW", "Chinesisch (Mandarin, Taiwan)", "zh-TW", "com.tw", "cmn-TW"),
)

_BY_ID = {v.id: v for v in VOICES}

DEFAULT_VOICE_ID = "en-GB"


def get_voice(voice_id: str | None) -> Voice:
    """Return the voice for ``voice_id`` or raise KeyError."""
    if voice_id not in _BY_ID:
        raise KeyError(f"Unbekannte Stimme: {voice_id!r}")
    return _BY_ID[voice_id]


def is_known_voice(voice_id: str | None) -> bool:
    return voice_id in _BY_ID


def google_translate_hosts() -> frozenset[str]:
    """Exact host names the Google Translate provider may contact."""
    return frozenset(f"translate.google.{v.gt_tld}" for v in VOICES)
