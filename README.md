# Aussprache per Knopfdruck – Anki-Add-on

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

Tipp für Notiztyp „Einfach (mit umgekehrter Karte)“: Hier stehen beide Felder auf einer
Vorderseite. Lege ein zusätzliches Feld `Audio` an und füge `{{Audio}}` nur in die
Rückseite der passenden Kartenvorlage ein.

Anki spielt Audio auf der Rückseite automatisch ab, solange in den Stapel-Optionen
„Audio nicht automatisch abspielen“ deaktiviert ist.

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
