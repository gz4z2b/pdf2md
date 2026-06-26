from pathlib import Path

from pdf2md.batch import (
    convert_directory,
    find_pdf_files,
    find_source_files,
    output_path_for,
    resources_path_for,
)


def test_find_pdf_files_recurses_and_matches_case_insensitive(tmp_path):
    origin = tmp_path / "origin"
    (origin / "sub").mkdir(parents=True)
    (origin / "a.pdf").write_bytes(b"")
    (origin / "sub" / "b.PDF").write_bytes(b"")
    (origin / "ignore.txt").write_text("ignore", encoding="utf-8")

    files = find_pdf_files(origin)

    assert [path.relative_to(origin).as_posix() for path in files] == [
        "a.pdf",
        "sub/b.PDF",
    ]


def test_find_source_files_includes_markdown_files(tmp_path):
    origin = tmp_path / "origin"
    (origin / "sub").mkdir(parents=True)
    (origin / "a.pdf").write_bytes(b"")
    (origin / "b.md").write_text("# Markdown", encoding="utf-8")
    (origin / "sub" / "c.MD").write_text("# Nested", encoding="utf-8")
    (origin / "ignore.txt").write_text("ignore", encoding="utf-8")

    files = find_source_files(origin)

    assert [path.relative_to(origin).as_posix() for path in files] == [
        "a.pdf",
        "b.md",
        "sub/c.MD",
    ]


def test_output_path_preserves_relative_directory(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "demo.pdf"

    assert output_path_for(source, origin, output) == output / "sub" / "demo.md"


def test_output_path_removes_trailing_note_suffix(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "04.为什么有人工作10年仍然平庸.note.pdf"

    assert output_path_for(source, origin, output) == (
        output / "sub" / "04.为什么有人工作10年仍然平庸.md"
    )


def test_resources_path_removes_trailing_note_suffix(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "demo.note.pdf"

    assert resources_path_for(source, origin, output) == output / "sources" / "sub" / "demo"


def test_output_path_keeps_markdown_filename(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "demo.MD"

    assert output_path_for(source, origin, output) == output / "sub" / "demo.MD"


def test_output_path_removes_trailing_note_suffix_from_markdown(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "demo.note.md"

    assert output_path_for(source, origin, output) == output / "sub" / "demo.md"


def test_convert_directory_converts_single_pdf(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/demo.pdf", ("Hello PDF",))

    summary = convert_directory(origin, output)

    assert summary.success_count == 1
    assert summary.failure_count == 0
    markdown = (output / "demo.md").read_text(encoding="utf-8")
    assert "# demo" in markdown
    assert "Hello PDF" in markdown


def test_convert_directory_copies_markdown_files(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "notes" / "demo.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Demo\n\n已有 Markdown 内容\n", encoding="utf-8")

    summary = convert_directory(origin, output)

    target = output / "notes" / "demo.md"
    assert summary.success_count == 1
    assert summary.failure_count == 0
    assert target.read_text(encoding="utf-8") == "# Demo\n\n已有 Markdown 内容\n"


def test_convert_directory_exports_pdf_images_to_sources(make_image_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_image_pdf("origin/sub/with-image.pdf")

    summary = convert_directory(origin, output)

    image_files = list((output / "sources" / "sub" / "with-image").iterdir())
    markdown = (output / "sub" / "with-image.md").read_text(encoding="utf-8")
    assert summary.success_count == 1
    assert summary.failure_count == 0
    assert len(image_files) == 1
    assert image_files[0].name.startswith("page-001-image-001.")
    assert "../sources/sub/with-image/" in markdown
    assert "![图片：第 1 张图片]" in markdown


def test_convert_directory_preserves_subdirectories(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/sub/demo.pdf", ("Nested PDF",))

    summary = convert_directory(origin, output)

    assert summary.success_count == 1
    assert (output / "sub" / "demo.md").exists()


def test_convert_directory_handles_missing_or_empty_input_dir(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"

    summary = convert_directory(origin, output)

    assert origin.exists()
    assert output.exists()
    assert summary.total_count == 0
    assert summary.success_count == 0
    assert summary.failure_count == 0


def test_convert_directory_records_broken_pdf_and_continues(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/good.pdf", ("Good PDF",))
    (origin / "broken.pdf").write_bytes(b"not a real pdf")

    summary = convert_directory(origin, output)

    assert summary.success_count == 1
    assert summary.failure_count == 1
    assert (output / "good.md").exists()
    assert summary.failed_files[0].source_path.name == "broken.pdf"


def test_convert_directory_skips_existing_output_without_overwrite(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/demo.pdf", ("New PDF",))
    output.mkdir()
    target = output / "demo.md"
    target.write_text("old content", encoding="utf-8")

    summary = convert_directory(origin, output, overwrite=False)

    assert summary.success_count == 0
    assert summary.skipped_count == 1
    assert target.read_text(encoding="utf-8") == "old content"


def test_convert_directory_overwrites_existing_output_by_default(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/demo.pdf", ("New PDF",))
    output.mkdir()
    target = output / "demo.md"
    target.write_text("old content", encoding="utf-8")

    summary = convert_directory(origin, output)

    assert summary.success_count == 1
    assert summary.skipped_count == 0
    assert "New PDF" in target.read_text(encoding="utf-8")


def test_convert_directory_removes_legacy_note_outputs(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/sub/demo.note.pdf", ("New PDF",))
    legacy_markdown = output / "sub" / "demo.note.md"
    legacy_resources = output / "sources" / "sub" / "demo.note"
    legacy_markdown.parent.mkdir(parents=True)
    legacy_markdown.write_text("old content", encoding="utf-8")
    legacy_resources.mkdir(parents=True)
    (legacy_resources / "old.png").write_bytes(b"old")

    summary = convert_directory(origin, output)

    assert summary.success_count == 1
    assert (output / "sub" / "demo.md").exists()
    assert not legacy_markdown.exists()
    assert not legacy_resources.exists()


def test_convert_directory_skips_existing_markdown_without_overwrite(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    origin.mkdir()
    output.mkdir()
    (origin / "demo.md").write_text("new markdown", encoding="utf-8")
    target = output / "demo.md"
    target.write_text("old markdown", encoding="utf-8")

    summary = convert_directory(origin, output, overwrite=False)

    assert summary.success_count == 0
    assert summary.skipped_count == 1
    assert target.read_text(encoding="utf-8") == "old markdown"
