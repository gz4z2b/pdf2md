import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import Pdf2MdError
from .markdown_writer import write_markdown_file
from .pdf_reader import read_pdf


SUPPORTED_SUFFIXES = {".pdf", ".md"}
NOTE_STEM_SUFFIX = ".note"


@dataclass(frozen=True)
class ConversionFailure:
    source_path: Path
    error: str


@dataclass(frozen=True)
class ConversionSummary:
    input_dir: Path
    output_dir: Path
    source_files: tuple[Path, ...]
    converted_files: tuple[Path, ...]
    skipped_files: tuple[Path, ...]
    failed_files: tuple[ConversionFailure, ...]

    @property
    def total_count(self) -> int:
        return len(self.source_files)

    @property
    def pdf_files(self) -> tuple[Path, ...]:
        return tuple(
            path for path in self.source_files if path.suffix.lower() == ".pdf"
        )

    @property
    def markdown_files(self) -> tuple[Path, ...]:
        return tuple(
            path for path in self.source_files if path.suffix.lower() == ".md"
        )

    @property
    def success_count(self) -> int:
        return len(self.converted_files)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped_files)

    @property
    def failure_count(self) -> int:
        return len(self.failed_files)

    @property
    def has_failures(self) -> bool:
        return self.failure_count > 0


def find_pdf_files(input_dir: Path) -> list[Path]:
    return [
        path
        for path in find_source_files(input_dir)
        if path.suffix.lower() == ".pdf"
    ]


def find_source_files(input_dir: Path) -> list[Path]:
    source_dir = Path(input_dir)
    if not source_dir.exists():
        return []

    return sorted(
        (
            path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda path: path.relative_to(source_dir).as_posix().lower(),
    )


def output_path_for(source_path: Path, input_dir: Path, output_dir: Path) -> Path:
    relative_path = _normalized_relative_path(source_path, input_dir)
    if source_path.suffix.lower() == ".md":
        return Path(output_dir) / relative_path
    return Path(output_dir) / relative_path.with_suffix(".md")


def resources_path_for(source_path: Path, input_dir: Path, output_dir: Path) -> Path:
    relative_path = _normalized_relative_path(source_path, input_dir).with_suffix("")
    return Path(output_dir) / "sources" / relative_path


def _normalized_relative_path(source_path: Path, input_dir: Path) -> Path:
    relative_path = source_path.relative_to(input_dir)
    stem = relative_path.stem
    if stem.lower().endswith(NOTE_STEM_SUFFIX):
        stem = stem[: -len(NOTE_STEM_SUFFIX)]
    return relative_path.with_name(f"{stem}{relative_path.suffix}")


def _legacy_output_path_for(source_path: Path, input_dir: Path, output_dir: Path) -> Path:
    relative_path = source_path.relative_to(input_dir)
    if source_path.suffix.lower() == ".md":
        return Path(output_dir) / relative_path
    return Path(output_dir) / relative_path.with_suffix(".md")


def _legacy_resources_path_for(
    source_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> Path:
    relative_path = source_path.relative_to(input_dir).with_suffix("")
    return Path(output_dir) / "sources" / relative_path


def _remove_legacy_note_outputs(
    source_path: Path,
    input_dir: Path,
    output_dir: Path,
    output_path: Path,
    resources_dir: Path | None = None,
) -> None:
    legacy_output_path = _legacy_output_path_for(source_path, input_dir, output_dir)
    if legacy_output_path != output_path and legacy_output_path.exists():
        legacy_output_path.unlink()

    if resources_dir is None:
        return

    legacy_resources_path = _legacy_resources_path_for(source_path, input_dir, output_dir)
    if legacy_resources_path != resources_dir and legacy_resources_path.exists():
        shutil.rmtree(legacy_resources_path)


def convert_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    overwrite: bool = True,
    logger: logging.Logger | None = None,
) -> ConversionSummary:
    source_dir = Path(input_dir)
    target_dir = Path(output_dir)
    log = logger or logging.getLogger("pdf2md")

    if not source_dir.exists():
        source_dir.mkdir(parents=True, exist_ok=True)
        log.info("未找到输入目录，已创建：%s", source_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    source_files = find_source_files(source_dir)

    if not source_files:
        log.info("没有找到 PDF 或 Markdown 文件：%s", source_dir)

    converted_files: list[Path] = []
    skipped_files: list[Path] = []
    failed_files: list[ConversionFailure] = []

    for source_path in source_files:
        output_path = output_path_for(source_path, source_dir, target_dir)

        if output_path.exists() and not overwrite:
            skipped_files.append(source_path)
            log.info("已存在，跳过：%s", output_path)
            continue

        try:
            if source_path.suffix.lower() == ".md":
                log.info("正在复制 Markdown：%s", source_path)
                _remove_legacy_note_outputs(source_path, source_dir, target_dir, output_path)
                copy_markdown_file(source_path, output_path, overwrite=True)
            else:
                log.info("正在转换：%s", source_path)
                document = read_pdf(source_path)
                resources_dir = resources_path_for(source_path, source_dir, target_dir)
                _remove_legacy_note_outputs(
                    source_path,
                    source_dir,
                    target_dir,
                    output_path,
                    resources_dir,
                )
                write_markdown_file(
                    document,
                    output_path,
                    overwrite=True,
                    resources_dir=resources_dir,
                )
            converted_files.append(output_path)
            log.info("已输出：%s", output_path)
        except Pdf2MdError as exc:
            failed_files.append(ConversionFailure(source_path=source_path, error=str(exc)))
            log.error("转换失败：%s：%s", source_path, exc)
        except Exception as exc:
            failed_files.append(ConversionFailure(source_path=source_path, error=str(exc)))
            log.error("转换失败：%s：%s", source_path, exc)

    return ConversionSummary(
        input_dir=source_dir,
        output_dir=target_dir,
        source_files=tuple(source_files),
        converted_files=tuple(converted_files),
        skipped_files=tuple(skipped_files),
        failed_files=tuple(failed_files),
    )


def copy_markdown_file(
    source_path: Path,
    output_path: Path,
    *,
    overwrite: bool = True,
) -> bool:
    source = Path(source_path)
    target = Path(output_path)
    if target.exists() and not overwrite:
        return False

    if source.resolve() == target.resolve():
        return True

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True
