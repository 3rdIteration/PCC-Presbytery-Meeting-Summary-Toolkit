"""
make_searchable_pdf.py
======================

Embed an invisible (PDF text rendering mode 3) text layer onto a scanned PDF
so its content becomes searchable in any PDF reader and parseable by
automated tools, while the original scanned image remains visually unchanged.

Typical workflow (for an AI agent):

    1. Detect a scanned PDF — one where pypdf returns essentially no text.
       Use `has_extractable_text(path)` from this module.
    2. Read each page with vision capability to OCR the content.
    3. Call this script (or `overlay_text()` directly) to bake the text in.

CLI usage:

    python make_searchable_pdf.py input.pdf pages.json [--output out.pdf] [--in-place]

    pages.json:  a JSON array of strings, one entry per page, in order.
                 Example:
                     ["Page 1 text...\nLine 2...", "Page 2 text...", "Page 3 text..."]

    --output PATH     Write to PATH (default: "<input stem> - searchable.pdf").
    --in-place        Replace the input file; original is backed up to
                      "<input>.bak" alongside it.

Library usage:

    from make_searchable_pdf import overlay_text, has_extractable_text

    if not has_extractable_text("scan.pdf"):
        pages = [...]  # one string per page, supplied by your OCR step
        overlay_text("scan.pdf", pages, "scan - searchable.pdf")

Notes
-----
- The overlay text is positioned as a left-aligned, wrapped block per page,
  not word-for-word over the scan. This means search and copy work, but
  selection highlights won't visually align with the scanned image. To get
  positional OCR (highlights aligned with scanned words), install Tesseract
  and use `ocrmypdf` instead.
- The original image content is preserved; this script only adds a layer.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from io import BytesIO
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


FONT_NAME = "Helvetica"
FONT_SIZE = 10
LEADING = 12
MARGIN = 54  # points (~0.75 inch)
TEXT_EMPTY_THRESHOLD = 20  # chars; below this, a page is treated as scanned


def has_extractable_text(pdf_path: str | Path, threshold: int = TEXT_EMPTY_THRESHOLD) -> bool:
    """Return True if the PDF already has a meaningful embedded text layer.

    A scanned PDF will return False (and is a candidate for OCR + overlay).
    """
    reader = PdfReader(str(pdf_path))
    total = 0
    for page in reader.pages:
        total += len(page.extract_text() or "")
        if total >= threshold:
            return True
    return False


def _build_overlay_page(text: str, width: float, height: float) -> bytes:
    """Build a single-page PDF (as bytes) with the given text rendered invisibly."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    text_obj = c.beginText()
    text_obj.setTextRenderMode(3)  # 3 = invisible: searchable/selectable but not drawn
    text_obj.setFont(FONT_NAME, FONT_SIZE)
    text_obj.setLeading(LEADING)
    text_obj.setTextOrigin(MARGIN, height - MARGIN)
    max_width = width - 2 * MARGIN

    for raw_line in (text or "").splitlines():
        if not raw_line.strip():
            text_obj.textLine("")
            continue
        # Word-wrap so long OCR lines don't drift off the page.
        words = raw_line.split(" ")
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            if stringWidth(trial, FONT_NAME, FONT_SIZE) <= max_width:
                line = trial
            else:
                if line:
                    text_obj.textLine(line)
                line = w
        if line:
            text_obj.textLine(line)

    c.drawText(text_obj)
    c.save()
    return buf.getvalue()


def overlay_text(
    input_pdf: str | Path,
    pages: Sequence[str],
    output_pdf: str | Path,
) -> Path:
    """Overlay the given per-page text onto `input_pdf` and write `output_pdf`.

    `pages` must have exactly one string per page in the input PDF.
    Empty strings are allowed (e.g. blank pages).
    Returns the output path.
    """
    input_path = Path(input_pdf)
    output_path = Path(output_pdf)

    reader = PdfReader(str(input_path))
    if len(pages) != len(reader.pages):
        raise ValueError(
            f"page count mismatch: PDF has {len(reader.pages)} pages, "
            f"got {len(pages)} text entries"
        )

    writer = PdfWriter()
    for page, text in zip(reader.pages, pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        overlay_bytes = _build_overlay_page(text, width, height)
        overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def _default_output_for(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem} - searchable.pdf")


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Embed an invisible searchable text layer onto a scanned PDF.",
    )
    parser.add_argument("input", help="Path to the scanned input PDF.")
    parser.add_argument(
        "pages_json",
        help='Path to a JSON file containing a list of strings, one per page.',
    )
    parser.add_argument(
        "--output",
        help="Path to write the searchable PDF. "
             "Default: '<input stem> - searchable.pdf' next to the input.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Replace the input file. The original is backed up to '<input>.bak'.",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    pages_json_path = Path(args.pages_json)
    try:
        pages_data = json.loads(pages_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"error: could not read pages JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(pages_data, list) or not all(isinstance(s, str) for s in pages_data):
        print("error: pages JSON must be a list of strings.", file=sys.stderr)
        return 2

    if args.in_place and args.output:
        print("error: --in-place and --output are mutually exclusive.", file=sys.stderr)
        return 2

    if args.in_place:
        backup = input_path.with_suffix(input_path.suffix + ".bak")
        shutil.copy2(input_path, backup)
        tmp_out = input_path.with_name(input_path.stem + ".tmp-searchable.pdf")
        overlay_text(input_path, pages_data, tmp_out)
        tmp_out.replace(input_path)
        print(f"wrote {input_path} (in-place); backup at {backup}")
    else:
        output_path = Path(args.output) if args.output else _default_output_for(input_path)
        overlay_text(input_path, pages_data, output_path)
        print(f"wrote {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
