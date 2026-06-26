import pytest
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

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


def test_read_pdf_removes_trailing_note_suffix_from_title(make_text_pdf):
    pdf_path = make_text_pdf("demo.note.pdf", ("Hello",))

    document = read_pdf(pdf_path)

    assert document.title == "demo"


def test_read_pdf_detects_images(make_image_pdf):
    pdf_path = make_image_pdf("with-image.pdf")

    document = read_pdf(pdf_path)

    assert len(document.pages) == 1
    assert document.pages[0].image_count >= 1
    assert len(document.pages[0].images) >= 1
    assert document.pages[0].images[0].page_number == 1
    assert document.pages[0].images[0].index == 1
    assert document.pages[0].images[0].extension
    assert document.pages[0].images[0].data


def test_read_pdf_extracts_detected_table_rows(tmp_path, capsys):
    pdf_path = tmp_path / "table.pdf"
    document_template = SimpleDocTemplate(str(pdf_path))
    table = Table([["Year", "Event"], ["2012", "Award"]])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    document_template.build([table])

    document = read_pdf(pdf_path)

    table_content = [
        content
        for content in document.pages[0].contents
        if content.kind == "table"
    ]
    assert table_content
    assert table_content[0].table_rows == (("Year", "Event"), ("2012", "Award"))
    assert "Consider using" not in capsys.readouterr().out


def test_read_pdf_ignores_single_row_layout_table(tmp_path):
    pdf_path = tmp_path / "single-row-layout.pdf"
    document_template = SimpleDocTemplate(str(pdf_path))
    table = Table([["Name", "Hello"]])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    document_template.build([table])

    document = read_pdf(pdf_path)

    table_content = [
        content
        for content in document.pages[0].contents
        if content.kind == "table"
    ]
    assert table_content == []
    assert "Name" in document.pages[0].text
    assert "Hello" in document.pages[0].text


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
