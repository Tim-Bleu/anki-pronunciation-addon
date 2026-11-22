**Pronunciation (TTS) – configuration / Konfiguration**

- `language`: `"auto"` (follow Anki / wie Anki), `"en"` or `"de"`. UI language of the add-on; takes effect after restarting Anki.
- `provider`: `"google_translate"` (free, no key / kostenlos, ohne Schlüssel) or `"google_cloud"` (official Google Cloud Text-to-Speech API, needs an API key / API-Schlüssel nötig).
- `default_voice`: default language/accent, e.g. `"en-GB"` (British), `"en-US"` (American), `"en-AU"`, `"fr-FR"`, `"fr-CA"`, `"es-ES"`, `"es-MX"`, `"pt-BR"`, `"pt-PT"`, `"de-DE"`, `"it-IT"`, `"ja-JP"` …
- `slow`: `true` = speak slowly / langsam sprechen (default for new note types).
- `google_cloud_api_key`: only for `google_cloud`. Sent only in an HTTPS header to `texttospeech.googleapis.com`.
- `google_cloud_voice_name`: optional, e.g. `"en-GB-Neural2-B"`; only used if it matches the chosen language.
- `replace_existing_audio`: `true` = replace audio previously inserted by this add-on / vorher eingefügte Audios ersetzen.
- `play_after_insert`: play the audio once after inserting / nach dem Einfügen einmal abspielen.
- `shortcut_generate` / `shortcut_settings`: editor shortcuts / Tastenkürzel im Editor.
- `note_types`: settings remembered per note type (source field, target field, voice, `placement`: `"field"` = back-side field, `"cloze_field"` = own field "Cloze Audio", only the current cloze plays (default for cloze note types), `"cloze"` = inside the cloze text; `cloze_text`: `"sentence"` or `"word"`). Maintained by the add-on – easiest to change with the second speaker button.
