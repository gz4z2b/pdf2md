from pathlib import Path

from pdf2md.batch import convert_directory, find_pdf_files, output_path_for


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


def test_output_path_preserves_relative_directory(tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    source = origin / "sub" / "demo.pdf"

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


def test_convert_directory_overwrites_when_requested(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/demo.pdf", ("New PDF",))
    output.mkdir()
    target = output / "demo.md"
    target.write_text("old content", encoding="utf-8")

    summary = convert_directory(origin, output, overwrite=True)

    assert summary.success_count == 1
    assert "New PDF" in target.read_text(encoding="utf-8")
