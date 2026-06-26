import contextlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz

from .errors import PdfReadError


@dataclass(frozen=True)
class PdfContent:
    kind: Literal["text", "table"]
    text: str = ""
    table_rows: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class PdfImage:
    page_number: int
    index: int
    extension: str
    data: bytes


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str
    image_count: int
    contents: tuple[PdfContent, ...] = ()
    images: tuple[PdfImage, ...] = ()


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
                    contents = _extract_page_contents(page)
                    text = "\n\n".join(
                        content.text
                        for content in contents
                        if content.kind == "text" and content.text
                    )
                    images = _extract_page_images(document, page, page_index)
                except Exception as exc:
                    raise PdfReadError(f"第 {page_index} 页无法读取：{exc}") from exc

                pages.append(
                    PdfPage(
                        number=page_index,
                        text=text,
                        image_count=len(images),
                        contents=contents,
                        images=images,
                    )
                )
    except PdfReadError:
        raise
    except Exception as exc:
        raise PdfReadError(f"文件无法读取：{source_path}") from exc

    return PdfDocument(
        source_path=source_path,
        title=_document_title(source_path),
        pages=tuple(pages),
    )


def _document_title(source_path: Path) -> str:
    stem = source_path.stem
    if stem.lower().endswith(".note"):
        return stem[:-5]
    return stem


def _extract_page_images(
    document: fitz.Document,
    page: fitz.Page,
    page_number: int,
) -> tuple[PdfImage, ...]:
    images: list[PdfImage] = []
    for image_index, image_info in enumerate(page.get_images(full=True), start=1):
        xref = image_info[0]
        try:
            extracted = document.extract_image(xref)
            data = extracted.get("image", b"")
            extension = _clean_image_extension(str(extracted.get("ext") or "bin"))
        except Exception:
            data = b""
            extension = "bin"

        images.append(
            PdfImage(
                page_number=page_number,
                index=image_index,
                extension=extension,
                data=data,
            )
        )
    return tuple(images)


def _clean_image_extension(extension: str) -> str:
    cleaned = extension.strip().lower().lstrip(".")
    if cleaned == "jpeg":
        return "jpg"
    if re.fullmatch(r"[a-z0-9]+", cleaned):
        return cleaned
    return "bin"


def _extract_page_contents(page: fitz.Page) -> tuple[PdfContent, ...]:
    tables = _extract_tables(page)
    table_bboxes = [bbox for bbox, _content in tables]

    items: list[tuple[tuple[float, float, float, float], PdfContent]] = []
    items.extend(tables)

    for block in page.get_text("blocks"):
        block_type = block[6] if len(block) > 6 else 0
        if block_type != 0:
            continue

        bbox = (float(block[0]), float(block[1]), float(block[2]), float(block[3]))
        if any(_intersects(bbox, table_bbox) for table_bbox in table_bboxes):
            continue

        text = _clean_text(block[4])
        if text:
            items.append((bbox, PdfContent(kind="text", text=text)))

    items.sort(key=lambda item: (round(item[0][1], 1), round(item[0][0], 1)))
    return tuple(content for _bbox, content in items)


def _extract_tables(
    page: fitz.Page,
) -> list[tuple[tuple[float, float, float, float], PdfContent]]:
    if not hasattr(page, "find_tables"):
        return []

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            table_finder = page.find_tables()
    except Exception:
        return []

    tables: list[tuple[tuple[float, float, float, float], PdfContent]] = []
    for table in table_finder.tables:
        rows = _clean_table_rows(table.extract())
        if not _looks_like_real_table(rows):
            continue
        bbox = tuple(float(value) for value in table.bbox)
        tables.append((bbox, PdfContent(kind="table", table_rows=rows)))

    return tables


def _looks_like_real_table(rows: tuple[tuple[str, ...], ...]) -> bool:
    if len(rows) < 2:
        return False

    width = max(len(row) for row in rows)
    if width < 2:
        return False

    normalized_rows = [_pad_row(row, width) for row in rows]
    header = normalized_rows[0]
    if _looks_like_table_header(header):
        return True

    return _looks_like_table_continuation(normalized_rows)


def _looks_like_table_header(row: tuple[str, ...]) -> bool:
    if not all(cell.strip() for cell in row):
        return False

    for cell in row:
        normalized = _single_line_text(cell)
        if len(normalized) > 18:
            return False
        if _looks_like_sentence(normalized):
            return False
        if normalized.startswith(("http://", "https://", "www.")):
            return False

    return True


def _looks_like_table_continuation(rows: list[tuple[str, ...]]) -> bool:
    if len(rows[0]) != 2:
        return False

    return any(
        _looks_like_year_cell(row[0]) and _contains_list_marker(row[1])
        for row in rows
    )


def _looks_like_sentence(text: str) -> bool:
    if len(text) > 24:
        return True
    return any(mark in text for mark in ("。", "，", "；", "！", "？", ",", ";", "?", "!"))


def _looks_like_year_cell(text: str) -> bool:
    return bool(re.match(r"^\s*\d{4}\s*年?\s*$", text))


def _contains_list_marker(text: str) -> bool:
    return any(marker in text for marker in ("\uf0d8", "", "", "•", "·", "●"))


def _single_line_text(text: str) -> str:
    return " ".join(text.split())


def _pad_row(row: tuple[str, ...], width: int) -> tuple[str, ...]:
    return row + tuple("" for _ in range(width - len(row)))


def _clean_table_rows(rows: list[list[str | None]]) -> tuple[tuple[str, ...], ...]:
    cleaned_rows: list[tuple[str, ...]] = []
    for row in rows:
        cleaned_row = tuple(_clean_text(cell or "") for cell in row)
        if any(cleaned_row):
            cleaned_rows.append(cleaned_row)
    return tuple(cleaned_rows)


def _clean_text(text: str) -> str:
    return "\n".join(
        line.strip()
        for line in text.replace("\xa0", " ").splitlines()
        if line.strip()
    )


def _intersects(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    return right > left and bottom > top
