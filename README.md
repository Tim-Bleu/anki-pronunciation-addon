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
1. `./scripts/build.sh` ausführen → `dist/pronunciation_tts.ankiaddon`
2. In Anki: *Extras → Add-ons → Aus Datei installieren…* und die Datei wählen.
3. Anki neu starten.

(Alternativ den Ordner `pronunciation_tts` in den Anki-Add-on-Ordner kopieren.)

## Benutzung
Im Editor erscheinen zwei Lautsprecher-Knöpfe:

| Knopf | Kürzel | Funktion |
|---|---|---|
| 🔊 | `Strg+Alt+P` | Aussprache sofort einfügen (mit den gemerkten Einstellungen) |
| 🔊⚙ | `Strg+Alt+Shift+P` | Felder, Sprache/Akzent und Dienst wählen |

Beim ersten Mal pro Notiztyp öffnet sich der Dialog:
- **Text vorlesen aus Feld** – das Feld mit dem Fremdwort/-satz (z. B. „Back“; bei Lückentext „Text“ – die Lücken werden komplett vorgelesen).
- **Audio einfügen in Feld** – ein Feld, das **nur auf der Rückseite** steht (z. B. „Back“, „Back Extra“ oder ein eigenes Feld „Audio“). Felder der Vorderseite werden abgelehnt, damit das Audio nichts verrät.
- **Sprache / Akzent** – z. B. Englisch (Britisch / Amerikanisch / Australisch / Indisch …), Französisch (Frankreich / Kanada), Spanisch (Spanien / Mexiko), Portugiesisch (Brasilien / Portugal) u. v. m.

### Audio direkt in die Lücke (Lückentext)
Bei Lückentext-Notizen kannst du im Dialog unter **„Audio einfügen“** die Option
**„Direkt in die Lücke (im Lückentext)“** wählen. Dann wird aus

    Stop being so {{c1::petty::kleinlich}}.

automatisch

    Stop being so {{c1::petty [sound:pron_en-GB_….mp3]::kleinlich}}.

Ein extra Feld brauchst du dafür nicht. Weil die Lücke auf der Vorderseite verdeckt ist, hörst
du das Audio erst nach dem Aufdecken. Unter **„Vorlesen“** wählst du:
- **Ganzen Satz vorlesen** – „Stop being so petty.“
- **Nur das Lückenwort vorlesen** – „petty“ (jede Lücke bekommt ihr eigenes Audio)

Hinweis: Hat eine Notiz mehrere Lücken-*Nummern* (`c1`, `c2` …), ist auf der Karte für c1
die Lücke c2 als normaler Text sichtbar, und deren Audio würde schon auf der Vorderseite
abgespielt. Das Add-on fragt in diesem Fall nach. Für solche Notizen ist „In ein Feld der
Rückseite“ (z. B. „Back Extra“) die bessere Wahl. Mehrere Lücken mit *derselben* Nummer
(`{{c1::…}} … {{c1::…}}`) sind kein Problem.

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
- **Google Cloud Text-to-Speech**: offizielle API mit sehr guten Stimmen pro Dialekt. API-Schlüssel unter *Extras → Add-ons → Konfiguration* eintragen und `"provider": "google_cloud"` setzen (oder im Dialog wählen).

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
