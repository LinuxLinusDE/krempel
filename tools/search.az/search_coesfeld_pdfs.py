#!/usr/bin/env python3
"""Download and search PDFs from https://coesfeld.eu/azcoe/ListE.php.

This script intentionally uses only Python's standard library. For extracting
PDF text it can use optional command line tools that are common on macOS:
pdftotext (best), mdls/mdimport (built in), or strings (weak fallback).
For scanned PDFs it can optionally use ocrmypdf when installed.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


LIST_URL = "https://coesfeld.eu/azcoe/ListE.php"
DEFAULT_DOWNLOAD_DIR = "pdfs"
DEFAULT_OCR_SUBDIR = "ocr"
DEFAULT_SCREENSHOT_DIR = "results/screenshots"
USER_AGENT = "Mozilla/5.0 (macOS; search-coesfeld-pdfs/1.0)"
OCR_BREW_PACKAGES = ["ocrmypdf", "tesseract-lang"]
SCREENSHOT_BREW_PACKAGES = ["poppler"]


@dataclass(frozen=True)
class PdfLink:
    name: str
    url: str
    date: str | None


@dataclass(frozen=True)
class SearchMatch:
    snippet: str
    page: int | None


class Console:
    def __init__(self, no_color: bool = False) -> None:
        self.is_tty = sys.stdout.isatty()
        self.color_enabled = self.is_tty and not no_color and not os.environ.get("NO_COLOR")
        self.width = min(shutil.get_terminal_size((100, 24)).columns, 120)

    def color(self, text: str, code: str) -> str:
        if not self.color_enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    def title(self, text: str) -> None:
        line = "=" * self.width
        print(self.color(line, "36"))
        print(self.color(text, "1;36"))
        print(self.color(line, "36"))

    def section(self, text: str) -> None:
        print()
        print(self.color(f"-- {text} " + "-" * max(0, self.width - len(text) - 4), "34"))

    def kv(self, key: str, value: object) -> None:
        print(f"  {self.color(key + ':', '1')} {value}")

    def status(self, label: str, message: str, detail: str | None = None, color: str = "37") -> None:
        badge = self.color(f"[{label:<7}]", color)
        if detail:
            print(f"{badge} {message} {self.color('- ' + detail, '2')}")
        else:
            print(f"{badge} {message}")

    def warn(self, message: str) -> None:
        self.status("WARN", message, color="33")

    def error(self, message: str) -> None:
        self.status("ERROR", message, color="31")

    def progress(self, label: str, current: int, total: int) -> None:
        if total <= 0 or not self.is_tty:
            return
        bar_width = 28
        done = min(bar_width, int(bar_width * current / total))
        bar = "#" * done + "-" * (bar_width - done)
        percent = min(100, int(100 * current / total))
        sys.stdout.write(f"\r{label} [{bar}] {percent:3d}% {human_bytes(current)}/{human_bytes(total)}")
        sys.stdout.flush()


def human_bytes(value: int | None) -> str:
    if value is None:
        return "unknown size"
    size = float(value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def date_range_label(from_date: str | None, to_date: str | None) -> str:
    if from_date and to_date:
        return f"{from_date} bis {to_date}"
    if from_date:
        return f"ab {from_date}"
    if to_date:
        return f"bis {to_date}"
    return "alle verfuegbaren Daten"


def fetch_text(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def find_pdf_links(html: str, base_url: str) -> list[PdfLink]:
    seen: set[str] = set()
    links: list[PdfLink] = []

    for href in re.findall(r'href=["\']([^"\']+\.pdf)["\']', html, flags=re.I):
        url = urllib.parse.urljoin(base_url, href)
        name = Path(urllib.parse.urlparse(url).path).name
        if not name or name in seen:
            continue
        seen.add(name)
        match = re.search(r"(\d{8})", name)
        links.append(PdfLink(name=name, url=url, date=match.group(1) if match else None))

    return links


def valid_yyyymmdd(value: str) -> str:
    if not re.fullmatch(r"\d{8}", value):
        raise argparse.ArgumentTypeError("expected date as YYYYMMDD, for example 20260728")
    return value


def prompt_required(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Bitte einen Wert eingeben.")


def prompt_optional_date(prompt: str) -> str | None:
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        try:
            return valid_yyyymmdd(value)
        except argparse.ArgumentTypeError:
            print("Bitte Datum im Format yyyymmdd eingeben, z.B. 20260728.")


def prompt_yes_no(prompt: str, default: bool = False) -> bool:
    default_hint = "J/n" if default else "j/N"
    while True:
        value = input(f"{prompt} [{default_hint}] ").strip().lower()
        if not value:
            return default
        if value in {"j", "ja", "y", "yes"}:
            return True
        if value in {"n", "nein", "no"}:
            return False
        print("Bitte j oder n eingeben.")


def fill_interactive_args(args: argparse.Namespace) -> None:
    print("Interaktive Suche fuer Coesfeld-PDFs")
    args.query = prompt_required("Suchbegriff: ")
    args.from_date = prompt_optional_date("Von Datum yyyymmdd (leer = ohne Startdatum): ")
    args.to_date = prompt_optional_date("Bis Datum yyyymmdd (leer = ohne Enddatum): ")
    args.ocr = prompt_yes_no("OCR fuer gescannte PDFs verwenden?", default=False)
    args.screenshots = prompt_yes_no("Screenshots von Trefferseiten speichern?", default=False)


def filter_links(
    links: list[PdfLink],
    from_date: str | None,
    to_date: str | None,
    limit: int | None,
) -> list[PdfLink]:
    filtered = []
    for link in links:
        if from_date and (not link.date or link.date < from_date):
            continue
        if to_date and (not link.date or link.date > to_date):
            continue
        filtered.append(link)
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def download_file(
    link: PdfLink,
    target_dir: Path,
    timeout: int,
    force: bool,
    console: Console,
    index: int,
    total: int,
) -> tuple[Path, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / link.name
    if target.exists() and target.stat().st_size > 0 and not force:
        console.status(
            "CACHE",
            f"[{index}/{total}] {target}",
            f"{human_bytes(target.stat().st_size)} bereits vorhanden",
            "33",
        )
        return target, "cached"

    request = urllib.request.Request(link.url, headers={"User-Agent": USER_AGENT})
    console.status("GET", f"[{index}/{total}] {link.name}", link.url, "36")
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_length = response.headers.get("Content-Length")
        total_bytes = int(content_length) if content_length and content_length.isdigit() else None
        fd, tmp_name = tempfile.mkstemp(prefix=f".{link.name}.", suffix=".part", dir=target_dir)
        try:
            written = 0
            with os.fdopen(fd, "wb") as tmp:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    written += len(chunk)
                    if total_bytes:
                        console.progress("  Download", written, total_bytes)
            if total_bytes and console.is_tty:
                print()
            Path(tmp_name).replace(target)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    elapsed = max(time.monotonic() - started, 0.001)
    size = target.stat().st_size
    console.status("SAVED", str(target), f"{human_bytes(size)} in {elapsed:.1f}s", "32")
    return target, "downloaded"


def run_command(args: list[str], timeout: int) -> str | None:
    try:
        result = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0 and not result.stdout:
        return None
    return result.stdout


def run_ocr_command(args: list[str], timeout: int, show_progress: bool) -> tuple[bool, str]:
    stderr_target = None if show_progress else subprocess.PIPE
    try:
        result = subprocess.run(
            args,
            check=False,
            stdout=subprocess.PIPE,
            stderr=stderr_target,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"OCR timed out after {timeout}s"
    except OSError as exc:
        return False, str(exc)

    captured_stderr = "" if show_progress else result.stderr
    output = "\n".join(part.strip() for part in [result.stdout, captured_stderr] if part and part.strip())
    return result.returncode == 0, output


def missing_ocr_tools(lang: str) -> list[str]:
    missing = []
    if not shutil.which("ocrmypdf"):
        missing.append("ocrmypdf")
    if not shutil.which("tesseract"):
        missing.append("tesseract")
    if shutil.which("tesseract") and lang == "deu":
        languages = run_command(["tesseract", "--list-langs"], timeout=20) or ""
        if "deu" not in {line.strip() for line in languages.splitlines()}:
            missing.append("tesseract-lang/deu")
    return missing


def install_ocr_tools(console: Console) -> bool:
    brew = shutil.which("brew")
    install_command = "brew install " + " ".join(OCR_BREW_PACKAGES)
    if not brew:
        console.warn("Homebrew wurde nicht gefunden. Bitte zuerst Homebrew installieren: https://brew.sh")
        console.warn(f"Danach OCR installieren mit: {install_command}")
        return False

    console.status("INSTALL", install_command, "Homebrew startet jetzt", "35")
    try:
        result = subprocess.run([brew, "install", *OCR_BREW_PACKAGES], check=False)
    except OSError as exc:
        console.error(f"Installation konnte nicht gestartet werden: {exc}")
        return False

    if result.returncode != 0:
        console.error(f"Installation fehlgeschlagen. Manuell versuchen: {install_command}")
        return False
    return True


def ensure_ocr_tools(lang: str, console: Console, allow_install_prompt: bool) -> bool:
    missing = missing_ocr_tools(lang)
    if not missing:
        console.status("OK", "OCR-Werkzeuge gefunden", "ocrmypdf/tesseract einsatzbereit", "32")
        return True

    install_command = "brew install " + " ".join(OCR_BREW_PACKAGES)
    console.warn("OCR ist aktiviert, aber benoetigte Werkzeuge fehlen.")
    console.kv("Fehlt", ", ".join(missing))
    console.kv("Installation", install_command)

    if not allow_install_prompt:
        console.warn("Automatische Installation wurde fuer diesen Lauf deaktiviert.")
        return False
    if not sys.stdin.isatty():
        console.warn("Automatische Installation wird nur in einem interaktiven Terminal angeboten.")
        return False

    if not prompt_yes_no("Fehlende OCR-Werkzeuge jetzt automatisch mit Homebrew installieren?", default=True):
        console.warn("OCR bleibt fuer diesen Lauf deaktiviert.")
        return False

    if not install_ocr_tools(console):
        console.warn("OCR bleibt fuer diesen Lauf deaktiviert.")
        return False

    missing_after_install = missing_ocr_tools(lang)
    if missing_after_install:
        console.warn("Nach der Installation fehlen noch OCR-Bestandteile.")
        console.kv("Fehlt weiterhin", ", ".join(missing_after_install))
        console.warn("OCR bleibt fuer diesen Lauf deaktiviert.")
        return False

    console.status("OK", "OCR-Werkzeuge installiert", "ocrmypdf/tesseract einsatzbereit", "32")
    return True


def install_screenshot_tools(console: Console) -> bool:
    brew = shutil.which("brew")
    install_command = "brew install " + " ".join(SCREENSHOT_BREW_PACKAGES)
    if not brew:
        console.warn("Homebrew wurde nicht gefunden. Bitte zuerst Homebrew installieren: https://brew.sh")
        console.warn(f"Danach Screenshot-Werkzeuge installieren mit: {install_command}")
        return False

    console.status("INSTALL", install_command, "Homebrew startet jetzt", "35")
    try:
        result = subprocess.run([brew, "install", *SCREENSHOT_BREW_PACKAGES], check=False)
    except OSError as exc:
        console.error(f"Installation konnte nicht gestartet werden: {exc}")
        return False

    if result.returncode != 0:
        console.error(f"Installation fehlgeschlagen. Manuell versuchen: {install_command}")
        return False
    return True


def ensure_screenshot_tools(console: Console, allow_install_prompt: bool) -> bool:
    if shutil.which("pdftoppm"):
        console.status("OK", "Screenshot-Werkzeuge gefunden", "pdftoppm/poppler einsatzbereit", "32")
        return True

    install_command = "brew install " + " ".join(SCREENSHOT_BREW_PACKAGES)
    console.warn("Screenshots sind aktiviert, aber pdftoppm aus Poppler fehlt.")
    console.kv("Fehlt", "pdftoppm")
    console.kv("Installation", install_command)

    if not allow_install_prompt:
        console.warn("Automatische Installation wurde fuer diesen Lauf deaktiviert.")
        return False
    if not sys.stdin.isatty():
        console.warn("Automatische Installation wird nur in einem interaktiven Terminal angeboten.")
        return False

    if not prompt_yes_no("Fehlende Screenshot-Werkzeuge jetzt automatisch mit Homebrew installieren?", default=True):
        console.warn("Screenshots bleiben fuer diesen Lauf deaktiviert.")
        return False

    if not install_screenshot_tools(console):
        console.warn("Screenshots bleiben fuer diesen Lauf deaktiviert.")
        return False

    if not shutil.which("pdftoppm"):
        console.warn("Nach der Installation wurde pdftoppm noch nicht gefunden.")
        console.warn("Screenshots bleiben fuer diesen Lauf deaktiviert.")
        return False

    console.status("OK", "Screenshot-Werkzeuge installiert", "pdftoppm/poppler einsatzbereit", "32")
    return True


def extract_with_pdftotext(path: Path, timeout: int) -> str | None:
    if not shutil.which("pdftotext"):
        return None
    return run_command(["pdftotext", "-layout", str(path), "-"], timeout)


def extract_with_mdls(path: Path, timeout: int, import_first: bool) -> str | None:
    if not shutil.which("mdls"):
        return None
    if import_first and shutil.which("mdimport"):
        run_command(["mdimport", str(path)], timeout)

    text = run_command(["mdls", "-raw", "-name", "kMDItemTextContent", str(path)], timeout)
    if not text:
        return None
    stripped = text.strip()
    if stripped in {"(null)", "null"}:
        return None
    return text


def extract_with_strings(path: Path, timeout: int) -> str | None:
    if not shutil.which("strings"):
        return None
    return run_command(["strings", str(path)], timeout)


def extract_text(
    path: Path,
    engine: str,
    timeout: int,
    import_first: bool,
    include_strings: bool = True,
) -> tuple[str | None, str]:
    engines = ["pdftotext", "mdls", "strings"] if engine == "auto" else [engine]
    if not include_strings:
        engines = [candidate for candidate in engines if candidate != "strings"]
    for candidate in engines:
        if candidate == "pdftotext":
            text = extract_with_pdftotext(path, timeout)
        elif candidate == "mdls":
            text = extract_with_mdls(path, timeout, import_first)
        elif candidate == "strings":
            text = extract_with_strings(path, timeout)
        else:
            raise ValueError(candidate)

        if text:
            return text, candidate
    return None, "none"


def is_skipped_ocr_sidecar(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and stripped.startswith("[OCR skipped on page(s)") and stripped.endswith("]")


def ocr_pdf(
    path: Path,
    source_dir: Path,
    ocr_dir: Path,
    lang: str,
    timeout: int,
    force: bool,
    console: Console,
) -> tuple[str | None, str]:
    if not shutil.which("ocrmypdf"):
        return None, "OCR ist aktiviert, aber ocrmypdf ist nicht installiert. Installation: brew install ocrmypdf tesseract-lang"

    try:
        relative = path.relative_to(source_dir)
    except ValueError:
        relative = Path(path.name)

    output_pdf = (ocr_dir / relative).with_suffix(".ocr.pdf")
    sidecar_txt = output_pdf.with_suffix(".txt")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    if sidecar_txt.exists() and sidecar_txt.stat().st_size > 0 and output_pdf.exists() and not force:
        cached_text = sidecar_txt.read_text(encoding="utf-8", errors="replace")
        if not is_skipped_ocr_sidecar(cached_text):
            console.status("OCR", str(path.name), "OCR-Text aus Cache", "33")
            return cached_text, "ocrmypdf-cache"
        console.warn(f"{path.name}: alter OCR-Cache enthaelt nur 'OCR skipped'; erstelle OCR neu")
        output_pdf.unlink()
        sidecar_txt.unlink()

    if output_pdf.exists() and force:
        output_pdf.unlink()
    if output_pdf.exists() and not sidecar_txt.exists():
        console.warn(f"{path.name}: OCR-PDF ohne Textcache gefunden; erstelle OCR neu")
        output_pdf.unlink()
    if sidecar_txt.exists() and force:
        sidecar_txt.unlink()

    show_progress = sys.stderr.isatty()
    progress_detail = "OCRmyPDF-Fortschritt folgt im Terminal" if show_progress else "keine TTY-Fortschrittsanzeige"
    console.status("OCR", str(path.name), f"language={lang}, timeout={timeout}s, {progress_detail}", "35")
    args = [
        "ocrmypdf",
        "--force-ocr",
        "--language",
        lang,
        "--sidecar",
        str(sidecar_txt),
        str(path),
        str(output_pdf),
    ]
    try:
        ok, message = run_ocr_command(args, timeout, show_progress=show_progress)
    except KeyboardInterrupt:
        output_pdf.unlink(missing_ok=True)
        sidecar_txt.unlink(missing_ok=True)
        console.warn(f"{path.name}: OCR abgebrochen, unvollstaendige OCR-Dateien entfernt")
        raise
    if not ok:
        return None, f"OCR fehlgeschlagen fuer {path}: {message}"
    if not sidecar_txt.exists():
        return None, f"OCR fertig, aber es wurde keine Textdatei geschrieben fuer {path}"
    return sidecar_txt.read_text(encoding="utf-8", errors="replace"), "ocrmypdf"


def iter_matches(
    text: str,
    query: str,
    case_sensitive: bool,
    context: int,
    max_matches: int,
) -> list[SearchMatch]:
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    matches = []
    pages = text.split("\f")
    use_page_numbers = len(pages) > 1
    for page_index, page_text in enumerate(pages, start=1):
        page_number = page_index if use_page_numbers else None
        for match in pattern.finditer(page_text):
            start = max(0, match.start() - context)
            end = min(len(page_text), match.end() + context)
            snippet = re.sub(r"\s+", " ", page_text[start:end]).strip()
            matches.append(SearchMatch(snippet=snippet, page=page_number))
            if len(matches) >= max_matches:
                return matches
    return matches


def render_pdf_page(
    pdf_path: Path,
    page: int,
    output_dir: Path,
    dpi: int,
    console: Console,
) -> Path | None:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        console.warn("Screenshot nicht moeglich: pdftoppm fehlt. Installation: brew install poppler")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = output_dir / f"{pdf_path.stem}_page-{page:03d}"
    output_png = output_prefix.with_suffix(".png")
    if output_png.exists() and output_png.stat().st_size > 0:
        console.status("SHOT", str(output_png), "bereits vorhanden", "33")
        return output_png

    console.status("SHOT", f"{pdf_path.name} Seite {page}", f"{output_png}", "35")
    result = subprocess.run(
        [
            pdftoppm,
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(output_prefix),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unbekannter Fehler"
        console.warn(f"Screenshot fehlgeschlagen fuer {pdf_path.name} Seite {page}: {message}")
        return None
    if not output_png.exists():
        console.warn(f"Screenshot-Befehl fertig, aber Datei fehlt: {output_png}")
        return None
    return output_png


def search_pdfs(
    paths: list[Path],
    query: str,
    engine: str,
    timeout: int,
    case_sensitive: bool,
    context: int,
    max_matches: int,
    only_matching_files: bool,
    import_first: bool,
    ocr: bool,
    ocr_dir: Path,
    ocr_lang: str,
    ocr_timeout: int,
    force_ocr: bool,
    source_dir: Path,
    console: Console,
    screenshots: bool,
    screenshot_dir: Path,
    screenshot_dpi: int,
) -> int:
    found_files = 0
    reported_missing_ocr = False
    for index, path in enumerate(paths, start=1):
        size = path.stat().st_size if path.exists() else None
        console.status("SCAN", f"[{index}/{len(paths)}] {path.name}", human_bytes(size), "36")
        text, used_engine = extract_text(
            path,
            engine,
            timeout,
            import_first,
            include_strings=not ocr,
        )
        matches = iter_matches(text, query, case_sensitive, context, max_matches) if text else []
        if text:
            console.status("TEXT", f"{path.name}", f"{used_engine}, {len(text):,} Zeichen", "34")
        else:
            console.status("TEXT", f"{path.name}", "keine lesbare Textebene gefunden", "33")

        if not matches and ocr:
            console.status("OCR?", f"{path.name}", "kein Treffer in normaler Textebene, versuche OCR", "35")
            ocr_text, ocr_engine_or_error = ocr_pdf(
                path=path,
                source_dir=source_dir,
                ocr_dir=ocr_dir,
                lang=ocr_lang,
                timeout=ocr_timeout,
                force=force_ocr,
                console=console,
            )
            if ocr_text:
                console.status("TEXT", f"{path.name}", f"OCR-Text, {len(ocr_text):,} Zeichen", "34")
                ocr_matches = iter_matches(ocr_text, query, case_sensitive, context, max_matches)
                if ocr_matches:
                    matches = ocr_matches
                    used_engine = ocr_engine_or_error
            elif "ocrmypdf ist nicht installiert" in ocr_engine_or_error:
                if not reported_missing_ocr:
                    console.warn(ocr_engine_or_error)
                    reported_missing_ocr = True
            else:
                console.warn(ocr_engine_or_error)

        if not text and not matches:
            console.status("SKIP", f"{path.name}", "nichts Durchsuchbares gefunden", "33")
            continue
        if not matches:
            console.status("MISS", f"{path.name}", "kein Treffer", "2")
            continue

        found_files += 1
        if only_matching_files:
            print(path)
            continue

        console.status("HIT", f"{path}", f"{len(matches)} angezeigte Treffer, Engine={used_engine}", "32")
        screenshot_pages: set[int] = set()
        for match_index, match in enumerate(matches, start=1):
            page_label = f"Seite {match.page}: " if match.page else ""
            print(f"    {console.color(str(match_index) + '.', '1;32')} {page_label}{match.snippet}")
            if screenshots and match.page and match.page not in screenshot_pages:
                screenshot_pages.add(match.page)
                render_pdf_page(path, match.page, screenshot_dir, screenshot_dpi, console)
            elif screenshots and not match.page:
                console.warn(f"{path.name}: keine Seitenzahl fuer Screenshot verfuegbar")

    return found_files


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and search PDFs from coesfeld.eu/azcoe/ListE.php",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="text to search for")
    parser.add_argument("--url", default=LIST_URL, help="PDF list URL")
    parser.add_argument("--dir", default=DEFAULT_DOWNLOAD_DIR, help="download directory")
    parser.add_argument("--from", dest="from_date", type=valid_yyyymmdd, help="first date as YYYYMMDD")
    parser.add_argument("--to", dest="to_date", type=valid_yyyymmdd, help="last date as YYYYMMDD")
    parser.add_argument("--limit", type=int, help="only process the first N PDFs from the list")
    parser.add_argument("--list", action="store_true", help="list matching PDFs without downloading")
    parser.add_argument("--download-only", action="store_true", help="download PDFs without searching")
    parser.add_argument("--force", action="store_true", help="download even if file already exists")
    parser.add_argument(
        "--engine",
        choices=["auto", "pdftotext", "mdls", "strings"],
        default="auto",
        help="text extraction engine",
    )
    parser.add_argument("--case-sensitive", action="store_true", help="case-sensitive search")
    parser.add_argument("--context", type=int, default=120, help="characters around each hit")
    parser.add_argument("--max-matches", type=int, default=5, help="max snippets per PDF")
    parser.add_argument("--only-matching-files", action="store_true", help="print only matching file paths")
    parser.add_argument("--no-mdimport", action="store_true", help="do not ask Spotlight to index PDFs first")
    parser.add_argument("--timeout", type=int, default=60, help="network and extraction timeout in seconds")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="run OCR with ocrmypdf if the normal text search finds no hit",
    )
    parser.add_argument("--ocr-dir", help="directory for OCR PDFs and OCR text cache")
    parser.add_argument("--ocr-lang", default="deu", help="OCR language for ocrmypdf/tesseract")
    parser.add_argument("--ocr-timeout", type=int, default=600, help="OCR timeout per PDF in seconds")
    parser.add_argument("--force-ocr", action="store_true", help="recreate existing OCR cache files")
    parser.add_argument("--screenshots", action="store_true", help="render matching PDF pages as PNG files")
    parser.add_argument("--screenshot-dir", default=DEFAULT_SCREENSHOT_DIR, help="directory for PNG screenshots")
    parser.add_argument("--screenshot-dpi", type=int, default=150, help="DPI for rendered PDF screenshots")
    parser.add_argument("--no-install-prompt", action="store_true", help="do not offer Homebrew installs")
    parser.add_argument("--no-color", action="store_true", help="disable colored terminal output")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    should_prompt = not args.query and not args.list and not args.download_only
    if not argv or (should_prompt and sys.stdin.isatty()):
        try:
            fill_interactive_args(args)
        except (EOFError, KeyboardInterrupt):
            print("\nAbgebrochen.", file=sys.stderr)
            return 130
    console = Console(no_color=args.no_color)

    if args.limit is not None and args.limit < 1:
        print("--limit must be greater than 0", file=sys.stderr)
        return 2
    if args.ocr_timeout < 1:
        print("--ocr-timeout must be greater than 0", file=sys.stderr)
        return 2
    if args.screenshot_dpi < 20:
        print("--screenshot-dpi must be at least 20", file=sys.stderr)
        return 2
    if args.from_date and args.to_date and args.from_date > args.to_date:
        print("--from must be before or equal to --to", file=sys.stderr)
        return 2
    if not args.query and not args.list and not args.download_only:
        print("Please provide a search query, --list, or --download-only.", file=sys.stderr)
        return 2

    target_dir = Path(args.dir)
    ocr_dir = Path(args.ocr_dir) if args.ocr_dir else target_dir / DEFAULT_OCR_SUBDIR
    screenshot_dir = Path(args.screenshot_dir)

    console.title("Coesfeld PDF Suche")
    if args.ocr and not args.list and not args.download_only:
        console.section("0. Werkzeuge pruefen")
        args.ocr = ensure_ocr_tools(
            lang=args.ocr_lang,
            console=console,
            allow_install_prompt=not args.no_install_prompt,
        )
    if args.screenshots and not args.list and not args.download_only:
        if not args.ocr:
            console.warn("Screenshots brauchen Seitenzahlen; bei gescannten PDFs ist --ocr meistens noetig.")
        console.section("0b. Screenshot-Werkzeuge pruefen")
        args.screenshots = ensure_screenshot_tools(
            console=console,
            allow_install_prompt=not args.no_install_prompt,
        )

    console.kv("Quelle", args.url)
    console.kv("Zeitraum", date_range_label(args.from_date, args.to_date))
    console.kv("Zielordner", target_dir)
    console.kv("Modus", "nur auflisten" if args.list else "download + suche")
    if args.query:
        console.kv("Suchbegriff", repr(args.query))
    console.kv("OCR", f"aktiv, Sprache={args.ocr_lang}, Cache={ocr_dir}" if args.ocr else "aus")
    console.kv("Screenshots", f"aktiv, Ordner={screenshot_dir}, DPI={args.screenshot_dpi}" if args.screenshots else "aus")

    console.section("1. PDF-Liste laden")
    console.status("GET", args.url, f"timeout={args.timeout}s", "36")

    try:
        html = fetch_text(args.url, args.timeout)
    except urllib.error.URLError as exc:
        console.error(f"PDF-Liste konnte nicht geladen werden: {exc}")
        return 1

    all_links = find_pdf_links(html, args.url)
    links = filter_links(
        all_links,
        from_date=args.from_date,
        to_date=args.to_date,
        limit=args.limit,
    )
    console.status("FOUND", f"{len(all_links)} PDF-Link(s) auf der Seite", color="32")
    console.status("FILTER", f"{len(links)} PDF(s) ausgewaehlt", date_range_label(args.from_date, args.to_date), "32")
    if not links:
        console.warn("Keine PDF-Links fuer den gewaehlten Filter gefunden.")
        return 1

    if args.list:
        console.section("Ausgewaehlte PDFs")
        for link in links:
            print(f"{link.name}\t{link.url}")
        console.section("Fertig")
        console.status("DONE", f"{len(links)} PDF(s) aufgelistet", color="32")
        return 0

    paths = []
    downloaded_count = 0
    cached_count = 0
    failed_count = 0
    console.section("2. PDFs herunterladen")
    start = time.monotonic()
    for index, link in enumerate(links, start=1):
        try:
            path, download_status = download_file(
                link,
                target_dir,
                args.timeout,
                args.force,
                console,
                index,
                len(links),
            )
            paths.append(path)
            if download_status == "cached":
                cached_count += 1
            else:
                downloaded_count += 1
        except urllib.error.URLError as exc:
            failed_count += 1
            console.error(f"{link.name}: {exc}")

    elapsed = time.monotonic() - start
    console.status(
        "READY",
        f"{len(paths)} PDF(s) bereit",
        f"{downloaded_count} geladen, {cached_count} aus Cache, {failed_count} Fehler, {elapsed:.1f}s",
        "32",
    )

    if args.download_only:
        console.section("Fertig")
        console.status("DONE", "Nur-Download-Lauf beendet", color="32")
        return 0

    console.section("3. PDFs durchsuchen")
    found_files = search_pdfs(
        paths=paths,
        query=args.query,
        engine=args.engine,
        timeout=args.timeout,
        case_sensitive=args.case_sensitive,
        context=args.context,
        max_matches=args.max_matches,
        only_matching_files=args.only_matching_files,
        import_first=not args.no_mdimport,
        ocr=args.ocr,
        ocr_dir=ocr_dir,
        ocr_lang=args.ocr_lang,
        ocr_timeout=args.ocr_timeout,
        force_ocr=args.force_ocr,
        source_dir=target_dir,
        console=console,
        screenshots=args.screenshots,
        screenshot_dir=screenshot_dir,
        screenshot_dpi=args.screenshot_dpi,
    )
    console.section("Zusammenfassung")
    console.kv("Gepruefte PDFs", len(paths))
    console.kv("Treffer-Dateien", found_files)
    console.kv("Downloads", downloaded_count)
    console.kv("Aus Cache", cached_count)
    console.kv("Fehler", failed_count)
    if args.screenshots:
        console.kv("Screenshot-Ordner", screenshot_dir)
    console.status("DONE", f"Treffer in {found_files} Datei(en).", color="32" if found_files else "33")
    return 0 if found_files else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
        raise SystemExit(130)
