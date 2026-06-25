from pathlib import Path

from pdf2md.markdown_writer import (
    BLANK_PAGE_PLACEHOLDER,
    build_markdown,
    image_placeholder,
    write_markdown_file,
)
from pdf2md.pdf_reader import PdfDocument, PdfPage


def test_build_markdown_writes_pages_text_images_and_blank_placeholder():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(number=1, text="Hello PDF", image_count=2),
            PdfPage(number=2, text="", image_count=0),
        ),
    )

    markdown = build_markdown(document)

    assert markdown.startswith("# demo\n")
    assert "## 第 1 页" in markdown
    assert "Hello PDF" in markdown
    assert image_placeholder(1, 1) in markdown
    assert image_placeholder(1, 2) in markdown
    assert "## 第 2 页" in markdown
    assert BLANK_PAGE_PLACEHOLDER in markdown
    assert markdown.endswith("\n")


def test_write_markdown_file_skips_existing_file_without_overwrite(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(PdfPage(number=1, text="New content", image_count=0),),
    )
    output_path = tmp_path / "demo.md"
    output_path.write_text("old content", encoding="utf-8")

    written = write_markdown_file(document, output_path, overwrite=False)

    assert written is False
    assert output_path.read_text(encoding="utf-8") == "old content"


def test_write_markdown_file_overwrites_when_requested(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(PdfPage(number=1, text="New content", image_count=0),),
    )
    output_path = tmp_path / "demo.md"
    output_path.write_text("old content", encoding="utf-8")

    written = write_markdown_file(document, output_path, overwrite=True)

    assert written is True
    assert "New content" in output_path.read_text(encoding="utf-8")
