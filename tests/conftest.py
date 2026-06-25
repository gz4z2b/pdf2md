import sys
from pathlib import Path

import fitz
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def make_text_pdf(tmp_path):
    def _make(relative_path: str, pages: tuple[str, ...] = ("Hello PDF",)) -> Path:
        pdf_path = tmp_path / relative_path
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        pdf_canvas = canvas.Canvas(str(pdf_path), pagesize=letter)
        for page_text in pages:
            if page_text:
                text_object = pdf_canvas.beginText(72, 720)
                for line in page_text.splitlines():
                    text_object.textLine(line)
                pdf_canvas.drawText(text_object)
            pdf_canvas.showPage()
        pdf_canvas.save()
        return pdf_path

    return _make


@pytest.fixture
def make_image_pdf(tmp_path):
    def _make(relative_path: str) -> Path:
        pdf_path = tmp_path / relative_path
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        document = fitz.open()
        page = document.new_page()
        pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 2, 2), False)
        pixmap.clear_with(0)
        page.insert_image(fitz.Rect(72, 72, 96, 96), pixmap=pixmap)
        document.save(pdf_path)
        document.close()
        return pdf_path

    return _make
