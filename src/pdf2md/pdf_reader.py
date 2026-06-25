from dataclasses import dataclass
from pathlib import Path

import fitz

from .errors import PdfReadError


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str
    image_count: int


@dataclass(frozen=True)
class PdfDocument:
    source_path: Path
    title: str
    pages: tuple[PdfPage, ...]


def read_pdf(path: Path) -> PdfDocument:
    source_path = Path(path)
    pages: list[PdfPage] = []

    try:
        with fitz.open(source_path) as document:
            for page_index, page in enumerate(document, start=1):
                try:
                    text = page.get_text("text").strip()
                    image_count = len(page.get_images(full=True))
                except Exception as exc:
                    raise PdfReadError(f"第 {page_index} 页无法读取：{exc}") from exc

                pages.append(
                    PdfPage(
                        number=page_index,
                        text=text,
                        image_count=image_count,
                    )
                )
    except PdfReadError:
        raise
    except Exception as exc:
        raise PdfReadError(f"文件无法读取：{source_path}") from exc

    return PdfDocument(
        source_path=source_path,
        title=source_path.stem,
        pages=tuple(pages),
    )
