# Aussprache per Knopfdruck – Anki-Add-on

🇬🇧 [English version](README.en.md)

> **Über dieses Projekt:** Das ist mein erstes Vibe-Coding-Projekt. Ich nutze es, um die
> Möglichkeiten von KI-Assistenten beim Programmieren kennenzulernen und mit der Zeit
> mitzuhalten. Der Code ist größtenteils KI-generiert und von mir angeleitet.

Fügt beim Erstellen oder Bearbeiten einer Karte per Klick eine **Aussprache-Audiodatei**
für das Fremdwort / den Fremdsatz ein – in der gewählten Sprache und dem gewählten
**Akzent** (z. B. britisches oder amerikanisches Englisch). Das Audio wird in ein Feld
der **Rückseite** gelegt und daher erst abgespielt, wenn du die Karte aufdeckst bzw. den
Lückentext beantwortet hast.

## Installation

**Einfachster Weg – fertige Datei herunterladen:**
1. Auf GitHub rechts unter **Releases** die neueste Version öffnen und
   `pronunciation_tts.ankiaddon` herunterladen.
2. Die Datei doppelt anklicken – Anki installiert sie. (Oder in Anki:
   *Extras → Add-ons → Aus Datei installieren…* und die Datei wählen.)
3. Anki neu starten.

**Selbst bauen** (z. B. für den neuesten Stand; nur Python nötig):
- Windows: `build.py` doppelt anklicken.
- macOS / Linux: im Projektordner `python3 build.py` ausführen.

Die Datei liegt danach unter `dist/pronunciation_tts.ankiaddon`.

(Alternativ den Ordner `pronunciation_tts` in den Anki-Add-on-Ordner kopieren:
*Extras → Add-ons → Add-on-Ordner anzeigen*.)

## Benutzung
Im Editor erscheinen zwei Lautsprecher-Knöpfe:

| Knopf | Kürzel | Funktion |
|---|---|---|
| 🔊 | `Strg+Alt+P` | Aussprache sofort einfügen (mit den gemerkten Einstellungen) |
| 🔊⚙ | `Strg+Alt+Shift+P` | Felder, Sprache/Akzent und Dienst wählen |

Die Oberfläche ist auf **Deutsch oder Englisch** – automatisch passend zur Sprache von Anki
(einstellbar über `"language"` in der Konfiguration).

Beim ersten Mal pro Notiztyp öffnet sich der Dialog; die Auswahl wird danach für den Notiztyp gemerkt:
- **Text vorlesen aus Feld** – das Feld mit dem Fremdwort/-satz (z. B. „Back“; bei Lückentext „Text“ – die Lücken werden komplett vorgelesen).
- **Audio einfügen in Feld** – ein Feld, das **nur auf der Rückseite** steht (z. B. „Back“, „Back Extra“ oder ein eigenes Feld „Audio“). Felder der Vorderseite werden abgelehnt, damit das Audio nichts verrät.
- **Audio einfügen** (nur bei Lückentext) – in ein Feld der Rückseite oder direkt in die Lücke (siehe unten).
- **Sprache / Akzent** – z. B. Englisch (Britisch / Amerikanisch / Australisch / Indisch …), Französisch (Frankreich / Kanada), Spanisch (Spanien / Mexiko), Portugiesisch (Brasilien / Portugal) u. v. m.

### Audio direkt in die Lücke (Lückentext)
Bei Lückentext-Notizen kannst du im Dialog unter **„Audio einfügen“** die Option
**„Direkt in die Lücke (im Lückentext)“** wählen. Dann wird aus

    Stop being so {{c1::petty::kleinlich}}.

automatisch

    Stop being so {{c1::petty [sound:pron_en-GB_….mp3]::kleinlich}}.

Ein extra Feld brauchst du dafür nicht. Weil die Lücke auf der Vorderseite verdeckt ist, hörst
du das Audio erst nach dem Aufdecken. Unter **„Vorlesen“** wählst du:
- **Ganzen Satz** – „Stop being so petty.“
- **Nur das Lückenwort** – „petty“ (jede Lücke bekommt ihr eigenes Audio)

**Mehrere Lücken = mehrere Fremdwörter:** Hat eine Notiz mehrere Lücken-*Nummern*
(`c1`, `c2` …), bekommt jede Lücke automatisch nur **ihr eigenes Wort** – auch wenn
„Ganzen Satz“ eingestellt ist:

    Stop being so {{c1::petty [sound:…petty…]::kleinlich}} and {{c2::rude [sound:…rude…]::unhöflich}}.

Auf der Karte für c1 ist die Lücke c2 als normaler Text sichtbar und wird daher schon auf
der Vorderseite vorgelesen. Das ist nur das sichtbare Wort – die gesuchte Lösung (c1) hörst
du erst nach dem Aufdecken. Mehrere Lücken mit *derselben* Nummer (`{{c1::…}} … {{c1::…}}`)
zählen als eine Lücke; dort gilt deine Einstellung.

Tipp für Notiztyp „Einfach (mit umgekehrter Karte)“: Hier stehen beide Felder auf einer
Vorderseite. Lege ein zusätzliches Feld `Audio` an und füge `{{Audio}}` nur in die
Rückseite der passenden Kartenvorlage ein.

Anki spielt Audio auf der Rückseite automatisch ab, solange in den Stapel-Optionen
„Audio nicht automatisch abspielen“ deaktiviert ist.

## Wo werden die Audiodateien gespeichert?
Im ganz normalen **Medienordner deiner Anki-Sammlung** (`collection.media`), also dort,
wo auch Bilder und andere Audios deiner Karten liegen:

| System | Ordner |
|---|---|
| Windows | `%APPDATA%\Anki2\<Profilname>\collection.media` |
| macOS | `~/Library/Application Support/Anki2/<Profilname>/collection.media` |
| Linux | `~/.local/share/Anki2/<Profilname>/collection.media` |

`<Profilname>` ist meist `Benutzer 1` bzw. `User 1`. Den Profilordner öffnest du in Anki über
*Datei → Profile wechseln → Profilordner öffnen*; darin liegt `collection.media`.

- Die Dateien heißen `pron_<Sprache>_<Kennung>.mp3`, z. B. `pron_en-GB_3f9c….mp3`.
- Sie werden wie alle Medien über **AnkiWeb synchronisiert**, sind also auch auf dem Handy (AnkiDroid / AnkiMobile) verfügbar.
- Wird eine Karte gelöscht oder das Audio ersetzt, bleibt die alte Datei zunächst liegen. *Extras → Medien überprüfen* zeigt ungenutzte Dateien an und kann sie löschen.

## Dienste
- **Google Translate** (Standard): kostenlos, kein Schlüssel. Der Akzent wird über die regionale Google-Domain gewählt (`translate.google.co.uk` = britisch, `.com` = amerikanisch …). Inoffizielle Schnittstelle – kann sich ändern.
- **Google Cloud Text-to-Speech**: offizielle API mit sehr guten Stimmen pro Dialekt. API-Schlüssel unter *Extras → Add-ons → Konfiguration* eintragen und `"provider": "google_cloud"` setzen.

## Sicherheit
Alle Downloads laufen über einen gehärteten HTTPS-Client:
nur HTTPS mit Zertifikats- und Hostnamenprüfung (TLS ≥ 1.2), feste Liste erlaubter Hosts,
keine Weiterleitungen, Zeit- und Größenlimits, Prüfung, dass wirklich eine MP3-Datei
geliefert wurde, lokal erzeugte Dateinamen, API-Schlüssel nur im HTTP-Header.
Gleiche Texte werden nicht erneut heruntergeladen (Cache über Dateinamen-Hash).

## Entwicklung
```bash
python3 -m pytest -q
```
Details für Entwickler/KI-Assistenten: siehe [CLAUDE.md](CLAUDE.md).

## Lizenz
Open Source unter der [GNU Affero General Public License v3.0 oder neuer](LICENSE)
(AGPL-3.0-or-later) – dieselbe Lizenz wie Anki selbst. Kostenlos: Du darfst den Code
nutzen, verändern und weitergeben; veränderte Versionen müssen ebenfalls als Open Source
unter dieser Lizenz veröffentlicht werden.
