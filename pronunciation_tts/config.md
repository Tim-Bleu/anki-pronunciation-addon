**Aussprache (TTS) – Konfiguration**

- `provider`: `"google_translate"` (kostenlos, ohne Schlüssel) oder `"google_cloud"` (offizielle Google Cloud Text-to-Speech API, API-Schlüssel nötig).
- `default_voice`: Standard-Sprache/Akzent, z. B. `"en-GB"` (britisch), `"en-US"` (amerikanisch), `"en-AU"`, `"fr-FR"`, `"fr-CA"`, `"es-ES"`, `"es-MX"`, `"pt-BR"`, `"pt-PT"`, `"de-DE"`, `"it-IT"`, `"ja-JP"` …
- `slow`: `true` = langsamer sprechen.
- `google_cloud_api_key`: nur für `google_cloud`. Wird nur per HTTPS-Header an `texttospeech.googleapis.com` gesendet.
- `google_cloud_voice_name`: optional, z. B. `"en-GB-Neural2-B"`. Wird nur verwendet, wenn er zur gewählten Sprache passt.
- `replace_existing_audio`: `true` = vorher von diesem Add-on eingefügte Audios im Zielfeld ersetzen.
- `play_after_insert`: Audio nach dem Einfügen einmal zur Kontrolle abspielen.
- `shortcut_generate` / `shortcut_settings`: Tastenkürzel im Editor.
- `note_types`: Gemerkte Einstellungen pro Notiztyp (Quellfeld, Zielfeld, Stimme). Wird vom Add-on selbst gepflegt.
