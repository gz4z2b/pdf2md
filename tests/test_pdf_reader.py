import pytest

from pdf2md.errors import PdfReadError
from pdf2md.pdf_reader import read_pdf


def test_read_pdf_extracts_text_pages(make_text_pdf):
    pdf_path = make_text_pdf("sample.pdf", ("Hello\nWorld", "Second page"))

    document = read_pdf(pdf_path)

    assert document.title == "sample"
    assert len(document.pages) == 2
    assert "Hello" in document.pages[0].text
    assert "World" in document.pages[0].text
    assert "Second page" in document.pages[1].text


def test_read_pdf_detects_images(make_image_pdf):
    pdf_path = make_image_pdf("with-image.pdf")

    document = read_pdf(pdf_path)

    assert len(document.pages) == 1
    assert document.pages[0].image_count >= 1


def test_read_pdf_keeps_blank_page(make_text_pdf):
    pdf_path = make_text_pdf("blank.pdf", ("",))

    document = read_pdf(pdf_path)

    assert len(document.pages) == 1
    assert document.pages[0].text == ""
    assert document.pages[0].image_count == 0


def test_read_pdf_raises_friendly_error_for_broken_pdf(tmp_path):
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a real pdf")

    with pytest.raises(PdfReadError, match="文件无法读取"):
        read_pdf(pdf_path)
