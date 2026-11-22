# CLAUDE.md – Anki add-on "Aussprache per Knopfdruck (TTS)"

## Vision
Anki add-on for language learners: while adding/editing a note that already
contains a foreign word/sentence, one click in the editor downloads a
pronunciation MP3 in the chosen language **and accent** (e.g. British vs.
American English) and inserts `[sound:…]` into a field that is shown **only on
the back side**. So the audio plays only after the card is revealed / the cloze
is answered – never on the question side.

## Layout
```
pronunciation_tts/        the add-on package (this folder is what gets zipped)
  __init__.py             only wires the GUI when running inside Anki
  editor_integration.py   editor buttons + shortcuts, QueryOp background download, config  [aqt]
  dialog.py               settings dialog (source field, placement/target, voice, slow) [aqt]
  i18n.py                 English/German UI strings, `tr()`                               [pure]
  core.py                 media filename, sound-tag insertion, template/front-side analysis [pure]
  providers.py            Google Translate (no key) + Google Cloud TTS (API key)           [pure]
  net.py                  hardened HTTPS client – the ONLY place allowed to do network I/O [pure]
  audio.py                MP3 validation                                                   [pure]
  text.py                 HTML/cloze/sound stripping, chunking                             [pure]
  voices.py               language/accent catalogue (+ derived host allow-list)            [pure]
  config.json / config.md default config + docs shown in Anki's config editor
  manifest.json           metadata for .ankiaddon installs
tests/                    pytest; test_anki_integration.py needs real anki+aqt (else skipped)
build.py                  builds dist/pronunciation_tts.ankiaddon (stdlib only, cross-platform)
.github/workflows/build.yml  CI: tests + build on push/PR; attaches the file to published releases
```
Modules marked **[pure]** must never import `aqt` or `anki` – that keeps them
unit-testable without Anki.

## Security rules (non-negotiable)
All downloads go through `net.request`. Never use `urllib`, `requests`,
`aqt.mw` HTTP helpers etc. directly anywhere else.
- HTTPS only; certificate + hostname verification on; TLS ≥ 1.2; certifi CA bundle when available.
- Exact host allow-list per request (Google Translate hosts are derived from `voices.py`; Cloud: `texttospeech.googleapis.com`). No wildcards / suffix matching.
- Redirects are refused, final URL re-checked.
- Timeouts and streamed response-size limits.
- Downloaded bytes must pass `audio.validate_mp3` (magic bytes, size) before being written.
- Media filenames are generated locally (`core.media_filename`, hash-based); never derived from server data. Written only via `col.media.write_data`.
- API keys go in headers (`X-Goog-Api-Key`), never in URLs or logs/error messages.
- Never disable TLS verification, not even in tests – tests use a local CA (`tests/test_net.py`).

## Behavioural rules
- Never insert audio into a field rendered on a front template (`core.field_on_front`); the dialog disables OK and `_run` re-checks.
- Exception, placement `"cloze"` (cloze note types only): the tag goes *inside* the deletion,
  `{{c1::petty [sound:pron_….mp3]::kleinlich}}` (before the hint). Anki hides the active deletion
  on the front, so it plays only on the back (verified via `card.question_av_tags()` in
  `tests/test_anki_integration.py`). Caveat: on card c2 the deletion c1 is visible on the front,
  so with several cloze numbers its audio plays there → dialog hint + `askUser` (default no).
  `cloze_text`: `"sentence"` (whole sentence, in the first deletion of each number) or `"word"`
  (each deletion gets audio of its own answer).
- `text.field_to_speech_text` must ignore our inserted tags (including their leading space), so the
  cache key stays the same after insertion.
- Cloze text: answers are spoken in full (`{{c1::x::hint}}` → `x`).
- Re-running replaces only this add-on's own tags (`[sound:pron_….mp3]`), never user audio.
- Same text+voice+speed+provider → same filename → cached, no new download.
- Network work runs in `QueryOp` (background thread); UI/note changes only in `success`.
- All user-visible strings go through `i18n.tr(key)`; every key needs `en` and `de` (enforced by
  `tests/test_i18n.py`). Language: config `language` = `auto` (follows Anki: `de*` → German, else English) / `en` / `de`.
- Keep the dialog minimal: fields, placement (cloze note types only), accent, slow. Service/API key live in the config.

## Commands
```bash
python3 -m pytest -q                                   # pure tests
pip install anki aqt[qt6] && QT_QPA_PLATFORM=offscreen python -m pytest -q tests/test_anki_integration.py
python3 build.py                                       # → dist/pronunciation_tts.ankiaddon
```
Target: Anki ≥ 23.10 (`min_point_version` 231000), Python ≥ 3.9 syntax with `from __future__ import annotations`.

## Releasing
Create a GitHub release (new tag, e.g. `v1.0.0`); the workflow attaches `pronunciation_tts.ankiaddon`.
The same file can be uploaded to AnkiWeb (ankiweb.net/shared/addons).

## Possible next steps
- Batch mode in the browser (generate for all selected notes).
- More providers (e.g. Azure / ElevenLabs) – add a `Provider` subclass, its exact host, tests.
- Optional automatic template check/fix offering to add an `{{Audio}}` field to the back template.
