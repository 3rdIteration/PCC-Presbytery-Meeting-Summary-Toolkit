"""
check_documents.py
==================
Detect and optionally repair damaged or invalid meeting documents.

Supported formats
-----------------
PDF    (.pdf)   — Check via pypdf strict mode; repair using pikepdf/QPDF
                  (preferred) or pypdf recovery mode as a fallback.
DOCX   (.docx)  — Check ZIP archive integrity and required internal structure.
XLSX   (.xlsx)
XLSM   (.xlsm)  — Same as DOCX.
DOC    (.doc)   — Check OLE2 compound-document magic bytes.
XLS    (.xls)   — Same as DOC.

CLI usage
---------
    python check_documents.py <file> [--repair] [--output <path>]

    --repair          Attempt repair for PDF files; writes a cleaned copy.
    --output PATH     Path for the repaired output.
                      Default: '<stem> - repaired.pdf' next to the input.

Exit codes
----------
    0  File is healthy.
    1  File is damaged but was successfully repaired (PDF only; --repair used).
    2  File is damaged; repair was not attempted, not supported, or failed.
    3  File is missing, unreadable, or could not be opened at all.

Library usage
-------------
    from check_documents import check_document_health, repair_pdf

    status, message = check_document_health("report.pdf")
    # status: "ok" | "damaged" | "unreadable"

    out_path = repair_pdf("report.pdf", "report - repaired.pdf")
    # Returns output path on success; raises RuntimeError on failure.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from typing import Literal, Tuple

HealthStatus = Literal["ok", "damaged", "unreadable"]

# OLE2 Compound Document magic bytes (DOC, XLS, PPT binary formats)
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Required internal paths for ZIP-based Office formats
_OFFICE_REQUIRED: dict[str, list[str]] = {
    ".docx": ["[Content_Types].xml", "word/document.xml"],
    ".xlsx": ["[Content_Types].xml", "xl/workbook.xml"],
    ".xlsm": ["[Content_Types].xml", "xl/workbook.xml"],
}


# ---------------------------------------------------------------------------
# PDF health check
# ---------------------------------------------------------------------------


def check_pdf_health(path: Path) -> Tuple[HealthStatus, str]:
    """Check whether a PDF can be opened in strict mode."""
    try:
        from pypdf import PdfReader
    except ImportError:
        # Fall back to pikepdf/QPDF if pypdf isn't available.
        try:
            import pikepdf  # type: ignore

            with pikepdf.open(str(path), suppress_warnings=True) as pdf:
                n = len(pdf.pages)
            return "ok", (
                f"Opened PDF via pikepdf/QPDF ({n} page(s)); "
                "pypdf is not installed so strict validation was not performed."
            )
        except ImportError:
            return (
                "unreadable",
                "Neither pypdf nor pikepdf is installed — run: pip install pypdf pikepdf",
            )
        except Exception as e:
            return "unreadable", f"PDF could not be opened via pikepdf/QPDF: {e}"
    strict_err: Exception | None = None

    # 1. Try strict mode (clean, no errors expected).
    try:
        reader = PdfReader(str(path), strict=True)
        n = len(reader.pages)  # trigger xref loading
        return "ok", f"Valid PDF ({n} page(s))."
    except Exception as e:
        strict_err = e

    # 2. Try pypdf lax recovery mode.
    try:
        reader = PdfReader(str(path), strict=False)
        n = len(reader.pages)
        return "damaged", (
            f"PDF is damaged (strict-mode error: {strict_err}), "
            f"but {n} page(s) appear recoverable via pypdf."
        )
    except Exception:
        pass

    # 3. Try pikepdf/QPDF, which handles truncated files and bad xref tables.
    try:
        import pikepdf  # type: ignore

        with pikepdf.open(str(path), suppress_warnings=True) as pdf:
            n = len(pdf.pages)
        return "damaged", (
            f"PDF is damaged (strict-mode error: {strict_err}), "
            f"but {n} page(s) appear recoverable via pikepdf/QPDF."
        )
    except ImportError:
        pass  # pikepdf not installed
    except Exception:
        pass

    return "unreadable", (
        f"PDF cannot be opened even in recovery mode. "
        f"Strict-mode error: {strict_err}"
    )


# ---------------------------------------------------------------------------
# PDF repair
# ---------------------------------------------------------------------------


def repair_pdf(input_path: str | Path, output_path: str | Path) -> Path:
    """Re-write a damaged PDF to produce a clean, valid copy.

    Tries pikepdf/QPDF first (handles truncation, bad xref, etc.) then falls
    back to pypdf recovery mode.  Raises RuntimeError if both fail.
    Returns the output path on success.
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try pikepdf (QPDF) — most capable for structural damage.
    pikepdf_err: Exception | None = None
    try:
        import pikepdf  # type: ignore

        with pikepdf.open(str(in_path), suppress_warnings=True) as pdf:
            pdf.save(str(out_path))
        return out_path
    except ImportError:
        pass  # not installed; fall through
    except Exception as e:
        pikepdf_err = e

    # 2. Fall back to pypdf recovery mode.
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(in_path), strict=False)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        if reader.metadata:
            writer.add_metadata(dict(reader.metadata))
        with open(out_path, "wb") as f:
            writer.write(f)
        return out_path
    except Exception as pypdf_err:
        detail = f"pypdf error: {pypdf_err}"
        if pikepdf_err:
            detail = f"pikepdf error: {pikepdf_err}; {detail}"
        raise RuntimeError(f"Repair failed. {detail}") from pypdf_err


# ---------------------------------------------------------------------------
# Office document health check (DOCX / XLSX / XLSM)
# ---------------------------------------------------------------------------


def check_office_zip_health(path: Path) -> Tuple[HealthStatus, str]:
    """Check if a DOCX/XLSX/XLSM ZIP archive is structurally valid."""
    ext = path.suffix.lower()
    required = _OFFICE_REQUIRED.get(ext, [])
    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            if bad:
                return "damaged", f"ZIP CRC error in internal file: {bad!r}"
            names = zf.namelist()
            for req in required:
                if req not in names:
                    return "damaged", f"Missing required internal file: {req!r}"
        return "ok", f"Valid {ext.upper().lstrip('.')} archive."
    except zipfile.BadZipFile as e:
        return "damaged", f"Not a valid ZIP archive: {e}"
    except Exception as e:
        return "unreadable", f"Could not open file: {e}"


# ---------------------------------------------------------------------------
# OLE2 health check (DOC / XLS binary formats)
# ---------------------------------------------------------------------------


def check_ole2_health(path: Path) -> Tuple[HealthStatus, str]:
    """Check if a DOC/XLS file has a valid OLE2 compound-document header."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        if len(header) < 8:
            return "damaged", "File is too small to be a valid OLE2 document."
        if header != _OLE2_MAGIC:
            return "damaged", f"Invalid OLE2 file header: {header.hex()}"
        return "ok", "OLE2 file header is valid."
    except Exception as e:
        return "unreadable", f"Could not read file: {e}"


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def check_document_health(path_like: str | Path) -> Tuple[HealthStatus, str]:
    """Check the health of any supported document type.

    Returns (status, message):
        "ok"         — file opened cleanly.
        "damaged"    — structural damage detected; some content may be recoverable.
        "unreadable" — file cannot be opened or format is not recognised.
    """
    path = Path(path_like)
    if not path.exists():
        return "unreadable", f"File not found: {path}"
    if path.stat().st_size == 0:
        return "damaged", "File is empty (0 bytes)."
    ext = path.suffix.lower()
    if ext == ".pdf":
        return check_pdf_health(path)
    if ext in _OFFICE_REQUIRED:
        return check_office_zip_health(path)
    if ext in (".doc", ".xls"):
        return check_ole2_health(path)
    return "ok", f"No structural check available for {ext!r} files."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_repair_output(p: Path) -> Path:
    return p.with_name(f"{p.stem} - repaired.pdf")


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check and optionally repair a document file.",
    )
    parser.add_argument("input", help="Path to the document to check.")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Attempt repair for PDF files and write a clean copy.",
    )
    parser.add_argument(
        "--output",
        help="Path for the repaired PDF. "
        "Default: '<stem> - repaired.pdf' next to the input.",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    status, message = check_document_health(input_path)

    label = {"ok": "OK", "damaged": "DAMAGED", "unreadable": "UNREADABLE"}[status]
    out_stream = sys.stderr if status == "unreadable" else sys.stdout
    print(f"{label}: {input_path.name} — {message}", file=out_stream)

    if status == "ok":
        return 0
    if status == "unreadable":
        return 3

    # status == "damaged"
    if not args.repair:
        return 2

    ext = input_path.suffix.lower()
    if ext != ".pdf":
        print(
            f"NOTE: Automatic repair is only supported for PDF files. "
            f"Cannot repair {ext!r}.",
            file=sys.stderr,
        )
        return 2

    output_path = Path(args.output) if args.output else _default_repair_output(input_path)
    try:
        repair_pdf(input_path, output_path)
        print(f"REPAIRED: wrote {output_path}")
        return 1
    except Exception as e:
        print(f"REPAIR FAILED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(_cli())
