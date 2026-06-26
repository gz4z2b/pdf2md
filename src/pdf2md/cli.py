import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from .batch import convert_directory
from .config import DEFAULT_INPUT_DIR, DEFAULT_LOG_LEVEL, DEFAULT_OUTPUT_DIR
from .logger import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="批量处理 PDF 和 Markdown 文档")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="源文件目录，默认 origin",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Markdown 输出目录，默认 output",
    )
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=True,
        help="替换已存在的 Markdown 文件，默认行为",
    )
    output_mode.add_argument(
        "--skip-existing",
        dest="overwrite",
        action="store_false",
        help="如果 Markdown 文件已存在，则跳过该文件",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="日志详细程度，默认 INFO",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    logger = logging.getLogger("pdf2md")

    summary = convert_directory(
        args.input_dir,
        args.output_dir,
        overwrite=args.overwrite,
        logger=logger,
    )

    logger.info(
        "完成：成功 %s 个，失败 %s 个，跳过 %s 个，输出目录：%s",
        summary.success_count,
        summary.failure_count,
        summary.skipped_count,
        summary.output_dir,
    )

    if summary.failed_files:
        logger.error("失败文件：")
        for failure in summary.failed_files:
            logger.error("- %s：%s", failure.source_path, failure.error)

    return 1 if summary.has_failures else 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
