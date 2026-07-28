# Third-Party Notices

This project does not vendor or redistribute third-party binaries, Python
packages, PDFs, or OCR data.

The repository code is licensed under the MIT License. Runtime tools mentioned
below are optional external programs installed separately by the user, usually
through Homebrew on macOS.

## Optional Runtime Tools

| Tool | Purpose | Typical install command | Upstream license |
| --- | --- | --- | --- |
| OCRmyPDF | Adds an OCR text layer to scanned PDFs | `brew install ocrmypdf` | MPL-2.0 |
| Tesseract OCR | OCR engine used by OCRmyPDF | `brew install tesseract` | Apache-2.0 |
| Tesseract language data | OCR language data, e.g. German | `brew install tesseract-lang` | See upstream package data |
| Poppler `pdftotext` | Optional text extraction engine, if installed | `brew install poppler` | See upstream package data |
| Poppler `pdftoppm` | Optional PNG rendering for matching PDF pages | `brew install poppler` | See upstream package data |

macOS tools such as `mdls`, `mdimport`, and `strings` are provided by the
operating system or developer tools and are not distributed by this repository.

## Downloaded PDFs

PDF files downloaded from `https://coesfeld.eu/azcoe/ListE.php` are not part of
this repository. The local `pdfs/` directory is ignored by Git. Do not publish
downloaded PDFs unless you have the necessary rights to do so.

## Notes For Redistribution

If you later bundle binaries, Docker images, packaged applications, OCR data,
or downloaded PDFs, additional license notices and redistribution obligations
may apply. This notice only covers the current repository layout, where those
components are installed or downloaded separately by the user.
