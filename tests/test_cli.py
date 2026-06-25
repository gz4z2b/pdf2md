from pathlib import Path

from pdf2md.cli import build_parser, run


def test_parser_defaults_match_documentation():
    args = build_parser().parse_args([])

    assert args.input_dir == Path("origin")
    assert args.output_dir == Path("output")
    assert args.overwrite is False
    assert args.log_level == "INFO"


def test_cli_run_converts_pdf(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/demo.pdf", ("CLI PDF",))

    exit_code = run(["--input-dir", str(origin), "--output-dir", str(output)])

    assert exit_code == 0
    assert "CLI PDF" in (output / "demo.md").read_text(encoding="utf-8")


def test_cli_run_returns_one_when_any_file_fails(make_text_pdf, tmp_path):
    origin = tmp_path / "origin"
    output = tmp_path / "output"
    make_text_pdf("origin/good.pdf", ("Good",))
    (origin / "broken.pdf").write_bytes(b"not a real pdf")

    exit_code = run(["--input-dir", str(origin), "--output-dir", str(output)])

    assert exit_code == 1
    assert (output / "good.md").exists()
