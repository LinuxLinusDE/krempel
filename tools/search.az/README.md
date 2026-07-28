# Coesfeld PDF Suche

Ein kleines macOS-CLI-Tool zum Herunterladen und Durchsuchen der PDFs aus der
Liste unter:

<https://coesfeld.eu/azcoe/ListE.php>

Das Skript kann einen Datumsbereich filtern, bereits heruntergeladene PDFs
wiederverwenden und optional OCR fuer gescannte PDFs einsetzen.

## Funktionen

- PDF-Liste automatisch von `coesfeld.eu` laden
- Datumsfilter im Format `yyyymmdd`
- PDFs lokal in `pdfs/` speichern
- Bereits vorhandene PDFs ueberspringen
- Normale Textsuche mit Kontextausgabe
- Optional OCR fuer gescannte PDFs
- Optional PNG-Screenshots der Trefferseiten
- Interaktiver Start ohne Argumente
- Ausfuehrliche Terminal-Ausgabe mit Status, Fortschritt und Zusammenfassung

## Voraussetzungen

macOS mit Python 3 reicht fuer Download und normale Suche:

```bash
python3 --version
```

Fuer OCR werden zusaetzlich `ocrmypdf` und Tesseract-Sprachdaten benoetigt.
Das Skript erkennt fehlende Werkzeuge und kann sie nach Rueckfrage automatisch
per Homebrew installieren.

Manuell geht das so:

```bash
brew install ocrmypdf tesseract-lang
```

Fuer Screenshots von Trefferseiten wird `pdftoppm` aus Poppler verwendet.
Auch hier erkennt das Skript fehlende Werkzeuge und kann sie nach Rueckfrage
installieren.

```bash
brew install poppler
```

## Nutzung

Interaktiv starten:

```bash
./search.pdf.sh
```

Direkt mit Suchbegriff und Zeitraum:

```bash
./search.pdf.sh "Glasfaser" --from 20260601 --to 20260610
```

Mit OCR:

```bash
./search.pdf.sh "Glasfaser" --from 20260601 --to 20260610 --ocr
```

Mit OCR und Screenshots der Trefferseiten:

```bash
./search.pdf.sh "Glasfaser" --from 20260601 --to 20260610 --ocr --screenshots
```

Nur PDF-Liste anzeigen:

```bash
./search.pdf.sh --list --from 20260601 --to 20260610
```

Nur herunterladen, nicht suchen:

```bash
./search.pdf.sh --download-only --from 20260601 --to 20260610
```

Farben deaktivieren:

```bash
./search.pdf.sh "Glasfaser" --from 20260601 --to 20260610 --no-color
```

## Downloads und Cache

Die PDFs werden standardmaessig nach `pdfs/` heruntergeladen. Dieser Ordner ist
in `.gitignore` eingetragen und wird nicht veroeffentlicht.

Wenn ein Download bereits vollstaendig vorhanden ist, wird er beim naechsten
Lauf wiederverwendet. Angefangene Downloads werden erst als temporare
`.part`-Dateien geschrieben und erst nach erfolgreichem Download zur PDF
umbenannt.

OCR-Ergebnisse werden unter `pdfs/ocr/` gecacht.
Wenn ein alter OCR-Cache nur einen `OCR skipped`-Hinweis enthaelt, wird er
automatisch verworfen und neu erstellt.
Bei langen OCR-Laeufen zeigt OCRmyPDF im interaktiven Terminal seine eigene
Fortschrittsanzeige an.

Screenshots werden standardmaessig unter `results/screenshots/` gespeichert.

## Wichtige Optionen

```text
--from yyyymmdd          Startdatum
--to yyyymmdd            Enddatum
--ocr                    OCR fuer gescannte PDFs verwenden
--ocr-lang deu           OCR-Sprache, Standard ist Deutsch
--force-ocr              Bestehenden OCR-Cache neu erstellen
--screenshots            Trefferseiten als PNG speichern
--screenshot-dir DIR     Ausgabeordner fuer Screenshots
--screenshot-dpi 150     Aufloesung der Screenshots
--only-matching-files    Nur Dateinamen mit Treffern ausgeben
--no-install-prompt      Keine automatische Homebrew-Installation anbieten
--no-color               Keine farbige Ausgabe
```

Alle Optionen:

```bash
./search.pdf.sh --help
```

## Hinweis

Bitte respektiere die Nutzungsbedingungen und Serverressourcen der Quellseite.
Das Skript speichert Dateien lokal und ueberspringt bereits vorhandene PDFs,
damit wiederholte Laeufe nicht unnoetig viel Traffic erzeugen.

## Lizenz

Der eigene Code steht unter der MIT License, siehe [LICENSE](LICENSE).

Drittanbieter-Werkzeuge werden nicht mitgeliefert, sondern nur optional zur
Laufzeit verwendet. Details stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
