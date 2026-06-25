import logging
from dataclasses import dataclass
from pathlib import Path

from .errors import Pdf2MdError
from .markdown_writer import write_markdown_file
from .pdf_reader import read_pdf


@dataclass(frozen=True)
class ConversionFailure:
    source_path: Path
    error: str


@dataclass(frozen=True)
class ConversionSummary:
    input_dir: Path
    output_dir: Path
    pdf_files: tuple[Path, ...]
    converted_files: tuple[Path, ...]
    skipped_files: tuple[Path, ...]
    failed_files: tuple[ConversionFailure, ...]

    @property
    def total_count(self) -> int:
        return len(self.pdf_files)

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
    source_dir = Path(input_dir)
    if not source_dir.exists():
        return []

    return sorted(
        (
            path
            for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.relative_to(source_dir).as_posix().lower(),
    )


def output_path_for(source_path: Path, input_dir: Path, output_dir: Path) -> Path:
    relative_path = source_path.relative_to(input_dir)
    return Path(output_dir) / relative_path.with_suffix(".md")


def convert_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    overwrite: bool = False,
    logger: logging.Logger | None = None,
) -> ConversionSummary:
    source_dir = Path(input_dir)
    target_dir = Path(output_dir)
    log = logger or logging.getLogger("pdf2md")

    if not source_dir.exists():
        source_dir.mkdir(parents=True, exist_ok=True)
        log.info("未找到输入目录，已创建：%s", source_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = find_pdf_files(source_dir)

    if not pdf_files:
        log.info("没有找到 PDF 文件：%s", source_dir)

    converted_files: list[Path] = []
    skipped_files: list[Path] = []
    failed_files: list[ConversionFailure] = []

    for source_path in pdf_files:
        output_path = output_path_for(source_path, source_dir, target_dir)

        if output_path.exists() and not overwrite:
            skipped_files.append(source_path)
            log.info("已存在，跳过：%s", output_path)
            continue

        try:
            log.info("正在转换：%s", source_path)
            document = read_pdf(source_path)
            write_markdown_file(document, output_path, overwrite=True)
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
        pdf_files=tuple(pdf_files),
        converted_files=tuple(converted_files),
        skipped_files=tuple(skipped_files),
        failed_files=tuple(failed_files),
    )
