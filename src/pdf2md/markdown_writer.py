import os
import re
import shutil
from pathlib import Path

from .pdf_reader import PdfContent, PdfDocument


BLANK_PAGE_PLACEHOLDER = "[本页没有可识别文字]"
ENDING_PUNCTUATION = set("。！？?!；;：:,，、.）)]】》」』”’\"'~")
ORDERED_LIST_RE = re.compile(r"^\s*(?:\(?(\d+)\)?|（(\d+)）)[、.．]\s*(.+)$")
ORDERED_MARKER_ONLY_RE = re.compile(r"^\s*(?:\(?\d+\)?|（\d+）)[、.．]\s*$")
PAREN_ORDERED_RE = re.compile(r"^\s*[\(（](\d+)[\)）]\s*(.+)$")
INLINE_PAREN_ORDERED_RE = re.compile(r"\s*[;；]?\s*[\(（](\d+)[\)）]\s*")
BULLET_RE = re.compile(r"^\s*(?:[\uf0d8•·●]|-(?!-)|\*(?!\*))\s*(.+)$")
BULLET_MARKER_ONLY_RE = re.compile(r"^\s*[\uf0d8•·●]\s*$")
CHINESE_SECTION_RE = re.compile(r"^[一二三四五六七八九十]+[、.．]\s*(.+)$")
DATE_LINE_RE = re.compile(r"^\d{1,2}号")
TOP_LINE_RE = re.compile(r"^Top\.(\d+)\s*(.+)$", re.IGNORECASE)
HORIZONTAL_RULE_RE = re.compile(r"^-{6,}$")
CLOSING_PHRASE_RE = re.compile(
    r"^(?:祝|收到请|Thanks\b|Best regards\b|Regards\b)", re.IGNORECASE
)
URL_START_RE = re.compile(r"^https?://|^www\.")
URL_ONLY_RE = re.compile(r"^(?:https?://|www\.)[A-Za-z0-9_./?&=%#:+-]+$")
URL_END_RE = re.compile(r"(?:https?://|www\.)[A-Za-z0-9_./?&=%#:+-]+$")
URL_CONTINUATION_RE = re.compile(r"^[A-Za-z0-9_./?&=%#:+-]+$")
URL_WITH_TRAILING_TEXT_RE = re.compile(
    r"(https?://[A-Za-z0-9_./?&=%#:+-]+)([\u4e00-\u9fff].*)"
)
EMPTY_PARENTHESES_RE = re.compile(r"([（(])\s*([）)])")
ATTACHMENT_FILE_RE = re.compile(r"^(.+\.(?:pdf|docx?|xlsx?|pptx?))$", re.IGNORECASE)
ATTACHMENT_SIZE_RE = re.compile(r"^(\d+(?:\.\s*\d+)?)\s*([KMG]B)$", re.IGNORECASE)
CLOSING_BRACKETS = ("）", ")", "】", "]", "》", "」", "』")
STRUCTURAL_LABELS = (
    "面试职位",
    "面试方式",
    "面试时间",
    "面试地点",
    "面谈时间",
    "面谈地点",
    "联系方式",
    "联系电话",
    "联系人",
    "联 系 人",
    "推荐职位",
    "职位名称",
    "面试岗位",
    "时间",
    "地址",
    "公司地址",
    "公司地点",
    "企业联系人",
    "坐车路线",
    "交通路线",
    "地铁",
    "公交快线",
    "自驾路线",
    "员工福利",
    "职位JD",
    "岗位职责",
    "职位描述",
    "职位要求",
    "任职要求",
    "优先考虑",
    "注意事项",
    "温馨提示",
    "公司简介",
    "公司提供",
    "携带物品",
    "Web",
)
STRUCTURAL_LABEL_PATTERN = "|".join(
    re.escape(label) for label in sorted(STRUCTURAL_LABELS, key=len, reverse=True)
)
LABEL_START_RE = re.compile(r"^(?:" + STRUCTURAL_LABEL_PATTERN + r")\s*[:：]")
EMBEDDED_LABEL_RE = re.compile(
    r"(?<!^)(?<![\u4e00-\u9fff])(?=(?:" + STRUCTURAL_LABEL_PATTERN + r")\s*[:：])"
)
EMBEDDED_TOP_RE = re.compile(r"(?<!^)(?=Top\.\d+\s*)", re.IGNORECASE)
HEADING_KEYWORDS = (
    "邀请函",
    "简介",
    "介绍",
    "职责",
    "要求",
    "待遇",
    "路线",
    "架构",
    "历程",
    "愿景",
    "理念",
    "业务",
    "发行",
    "最后",
    "排行",
)
NOTE_SECTION_HEADINGS = {
    "今天完成",
    "今日完成",
    "重要紧急",
    "重要不紧急",
    "紧急重要",
    "紧急不重要",
    "不重要不紧急",
}


def image_placeholder(image_index: int) -> str:
    return f"[图片占位符：第 {image_index} 张图片]"


def image_markdown(image_index: int, image_path: str) -> str:
    return f"![图片：第 {image_index} 张图片]({image_path})"


def build_markdown(
    document: PdfDocument,
    *,
    image_links: dict[tuple[int, int], str] | None = None,
) -> str:
    lines = [f"# {document.title}"]
    last_table_header: tuple[str, ...] | None = None
    image_counter = 0
    links = image_links or {}

    for page in document.pages:
        blocks: list[str] = []
        for content in _coalesce_text_contents(
            page.contents or _legacy_text_content(page.text),
        ):
            if content.kind == "table":
                table_markdown, last_table_header = _format_table(
                    content.table_rows,
                    last_table_header,
                )
                if table_markdown:
                    if blocks and _is_table_continuation(table_markdown, blocks[-1]):
                        blocks[-1] = f"{blocks[-1].rstrip()}\n{table_markdown}"
                    else:
                        blocks.append(table_markdown)
            elif content.text:
                blocks.append(_format_text_block(content.text))

        if page.images:
            for image in page.images:
                image_counter += 1
                image_path = links.get((page.number, image.index))
                if image_path:
                    blocks.append(image_markdown(image_counter, image_path))
                else:
                    blocks.append(image_placeholder(image_counter))
        else:
            for _image_index in range(page.image_count):
                image_counter += 1
                blocks.append(image_placeholder(image_counter))

        blocks = _attach_url_blocks_to_empty_parentheses(blocks)
        blocks = _merge_adjacent_formatted_blocks(blocks)

        if not blocks:
            blocks.append(BLANK_PAGE_PLACEHOLDER)

        for block in blocks:
            if _is_table_rows_only_block(block) and _last_emitted_line(lines).startswith("|"):
                lines.append(block.rstrip())
            elif _is_ordered_markdown_block(block) and _is_ordered_markdown_line(
                _last_emitted_line(lines),
            ):
                lines.append(block.rstrip())
            else:
                lines.extend(["", block.rstrip()])

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_file(
    document: PdfDocument,
    output_path: Path,
    *,
    overwrite: bool = True,
    resources_dir: Path | None = None,
) -> bool:
    target_path = Path(output_path)
    if target_path.exists() and not overwrite:
        return False

    image_links: dict[tuple[int, int], str] | None = None
    if resources_dir is not None:
        image_links = _write_image_files(document, Path(resources_dir), target_path)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(build_markdown(document, image_links=image_links), encoding="utf-8")
    return True


def _write_image_files(
    document: PdfDocument,
    resources_dir: Path,
    output_path: Path,
) -> dict[tuple[int, int], str]:
    if resources_dir.exists():
        shutil.rmtree(resources_dir)

    image_links: dict[tuple[int, int], str] = {}
    for page in document.pages:
        for image in page.images:
            if not image.data:
                continue

            resources_dir.mkdir(parents=True, exist_ok=True)
            image_path = resources_dir / (
                f"page-{image.page_number:03d}-image-{image.index:03d}.{image.extension}"
            )
            image_path.write_bytes(image.data)
            image_links[(image.page_number, image.index)] = _relative_markdown_path(
                image_path,
                output_path,
            )

    return image_links


def _relative_markdown_path(target_path: Path, markdown_path: Path) -> str:
    relative_path = os.path.relpath(target_path, start=markdown_path.parent)
    return relative_path.replace(os.sep, "/")


def _legacy_text_content(text: str) -> tuple[PdfContent, ...]:
    if not text:
        return ()
    return (PdfContent(kind="text", text=text),)


def _is_table_continuation(table_markdown: str, previous_block: str) -> bool:
    return (
        previous_block.lstrip().startswith("|")
        and table_markdown.lstrip().startswith("|")
        and "| ---" not in table_markdown
    )


def _is_table_rows_only_block(block: str) -> bool:
    return block.lstrip().startswith("|") and "| ---" not in block


def _last_emitted_line(lines: list[str]) -> str:
    for item in reversed(lines):
        for line in reversed(item.splitlines()):
            stripped = line.strip()
            if stripped:
                return stripped
    return ""


def _is_ordered_markdown_block(block: str) -> bool:
    first_line = _first_nonempty_line(block)
    return _is_ordered_markdown_line(first_line)


def _is_ordered_markdown_line(line: str) -> bool:
    return bool(_format_ordered_line(_normalize_spacing(line)))


def _coalesce_text_contents(contents: tuple[PdfContent, ...]) -> tuple[PdfContent, ...]:
    coalesced: list[PdfContent] = []
    pending_text = ""

    for content in contents:
        if content.kind != "text":
            if pending_text:
                coalesced.append(PdfContent(kind="text", text=pending_text))
                pending_text = ""
            coalesced.append(content)
            continue

        if not content.text:
            continue

        if pending_text and _should_merge_text_blocks(pending_text, content.text):
            pending_text = f"{pending_text.rstrip()}\n{content.text.lstrip()}"
            continue

        if pending_text:
            coalesced.append(PdfContent(kind="text", text=pending_text))
        pending_text = content.text

    if pending_text:
        coalesced.append(PdfContent(kind="text", text=pending_text))

    return tuple(coalesced)


def _format_text_block(text: str) -> str:
    source_lines = _prepare_text_lines(text)
    formatted_lines: list[str] = []

    for line in source_lines:
        formatted_lines.extend(_format_text_line(line, standalone=len(source_lines) == 1))

    formatted_lines = _merge_list_continuations(formatted_lines)
    return "\n".join(formatted_lines)


def _format_text_line(line: str, *, standalone: bool) -> list[str]:
    normalized = _normalize_spacing(line)
    if not normalized:
        return []

    top_line = TOP_LINE_RE.match(normalized)
    if top_line:
        return [f"{top_line.group(1)}. {top_line.group(2).strip()}"]

    chinese_section = CHINESE_SECTION_RE.match(normalized)
    if chinese_section and len(normalized) <= 40:
        return [f"## {normalized}"]

    bullet_match = BULLET_RE.match(normalized)
    if bullet_match:
        return [f"- {bullet_match.group(1).strip()}"]

    ordered_line = _format_ordered_line(normalized)
    if ordered_line:
        return [ordered_line]

    if _has_inline_ordered_items(normalized):
        return _split_inline_ordered_items(normalized)

    if _looks_like_heading(normalized):
        return [f"## {normalized}"]

    return [normalized]


def _format_ordered_line(line: str) -> str | None:
    match = ORDERED_LIST_RE.match(line)
    if match:
        number = match.group(1) or match.group(2)
        return f"{number}. {match.group(3).strip()}"

    match = PAREN_ORDERED_RE.match(line)
    if match:
        return f"{match.group(1)}. {match.group(2).strip()}"

    return None


def _has_inline_ordered_items(line: str) -> bool:
    matches = _inline_ordered_matches(line)
    return bool(matches)


def _split_inline_ordered_items(line: str) -> list[str]:
    parts: list[str] = []
    matches = _inline_ordered_matches(line)
    first_match = matches[0]
    prefix = line[: first_match.start()].strip()
    if prefix:
        parts.append(prefix)

    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(line)
        content = line[match.end() : next_start].strip()
        if content:
            parts.append(f"{match.group(1)}. {content}")

    return parts


def _inline_ordered_matches(line: str) -> list[re.Match[str]]:
    return [
        match
        for match in INLINE_PAREN_ORDERED_RE.finditer(line)
        if 1 <= int(match.group(1)) <= 50
    ]


def _merge_list_continuations(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if merged and _should_merge_list_continuation(merged[-1], line):
            merged[-1] = _join_lines(merged[-1], line)
            continue
        merged.append(line)
    return merged


def _should_merge_list_continuation(previous: str, current: str) -> bool:
    if not re.match(r"^\d+\.\s+", previous):
        return False
    if _is_structural_formatted_line(current):
        return False
    if previous[-1] in "。！？!?；;":
        return False
    return len(previous) <= 12 or _looks_like_wrapped_tail(previous, current)


def _looks_like_heading(line: str) -> bool:
    if len(line) > 36:
        return False
    if re.fullmatch(r"[\d\s]+", line):
        return False
    if re.search(r"\d", line):
        return False
    if not re.search(r"[\u4e00-\u9fff]", line):
        return False
    if line.startswith(CLOSING_BRACKETS):
        return False
    if "|" in line or "@" in line or "=" in line:
        return False
    if line.startswith(("http://", "https://", "www.")):
        return False
    if any(mark in line for mark in ("：", ":", "，", ",", "；", ";", "。", ".")):
        return False
    if line[-1] in ENDING_PUNCTUATION:
        return False
    if _format_ordered_line(line):
        return False
    if _is_note_section_heading(line):
        return True
    return any(keyword in line for keyword in HEADING_KEYWORDS)


def _format_table(
    rows: tuple[tuple[str, ...], ...],
    previous_header: tuple[str, ...] | None,
) -> tuple[str, tuple[str, ...] | None]:
    if not rows:
        return "", previous_header

    width = max(len(row) for row in rows)
    normalized_rows = [_pad_row(row, width) for row in rows]

    continued_rows_only = False
    if previous_header and normalized_rows[0] == previous_header:
        header = previous_header
        data_rows = normalized_rows[1:]
        continued_rows_only = True
    elif _row_can_be_header(normalized_rows[0]):
        header = normalized_rows[0]
        data_rows = normalized_rows[1:]
    elif previous_header and len(previous_header) == width:
        header = previous_header
        data_rows = normalized_rows
        continued_rows_only = True
    else:
        header = tuple(f"列 {index}" for index in range(1, width + 1))
        data_rows = normalized_rows

    table_lines: list[str] = []
    if not continued_rows_only:
        table_lines.extend(
            [
                _markdown_table_row(header),
                _markdown_table_row(tuple("---" for _ in range(width))),
            ]
        )
    table_lines.extend(_markdown_table_row(row) for row in data_rows)
    return "\n".join(table_lines), header


def _row_can_be_header(row: tuple[str, ...]) -> bool:
    return bool(row) and all(cell.strip() for cell in row)


def _pad_row(row: tuple[str, ...], width: int) -> tuple[str, ...]:
    return row + tuple("" for _ in range(width - len(row)))


def _markdown_table_row(row: tuple[str, ...]) -> str:
    return "| " + " | ".join(_format_table_cell(cell) for cell in row) + " |"


def _format_table_cell(cell: str) -> str:
    lines: list[str] = []
    for raw_line in cell.splitlines():
        line = _normalize_spacing(raw_line)
        if not line:
            continue
        bullet_match = BULLET_RE.match(line)
        if bullet_match:
            lines.append(f"- {bullet_match.group(1).strip()}")
            continue
        ordered_line = _format_ordered_line(line)
        lines.append(ordered_line or line)

    return "<br>".join(lines).replace("|", "\\|")


def _normalize_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _prepare_text_lines(text: str) -> list[str]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    structural_lines = _split_structural_lines(raw_lines)
    merged_lines = _attach_urls_to_empty_parentheses(
        _merge_wrapped_lines(_merge_url_lines(structural_lines)),
    )
    return _format_attachment_lines(_remove_orphan_bullet_markers(merged_lines))


def _split_structural_lines(lines: list[str]) -> list[str]:
    split_lines: list[str] = []
    for line in lines:
        for part in _split_structural_line(line):
            normalized = _normalize_spacing(part)
            if normalized:
                split_lines.append(normalized)
    return split_lines


def _split_structural_line(line: str) -> list[str]:
    parts = [line]
    splitters = (
        _split_horizontal_rule_prefix,
        _split_embedded_top_lines,
        _split_embedded_label_lines,
        _split_url_trailing_text,
    )
    for splitter in splitters:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(splitter(part))
        parts = next_parts
    return parts


def _split_horizontal_rule_prefix(line: str) -> list[str]:
    match = re.match(r"^(-{6,})([^-].*)$", line.strip())
    if not match:
        return [line]
    return [match.group(1), match.group(2)]


def _split_embedded_top_lines(line: str) -> list[str]:
    return _split_by_boundary(line, EMBEDDED_TOP_RE)


def _split_embedded_label_lines(line: str) -> list[str]:
    return _split_by_boundary(line, EMBEDDED_LABEL_RE)


def _split_url_trailing_text(line: str) -> list[str]:
    match = URL_WITH_TRAILING_TEXT_RE.search(line)
    if not match:
        return [line]
    prefix = line[: match.start()].strip()
    url = match.group(1).strip()
    trailing = match.group(2).strip()
    parts = [part for part in (prefix, url, trailing) if part]
    return parts or [line]


def _split_by_boundary(line: str, boundary_re: re.Pattern[str]) -> list[str]:
    parts = [part.strip() for part in boundary_re.split(line) if part.strip()]
    return parts or [line]


def _remove_orphan_bullet_markers(lines: list[str]) -> list[str]:
    return [line for line in lines if not BULLET_MARKER_ONLY_RE.match(line)]


def _format_attachment_lines(lines: list[str]) -> list[str]:
    formatted: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        if index + 1 < len(lines):
            file_match = ATTACHMENT_FILE_RE.match(current)
            size_match = ATTACHMENT_SIZE_RE.match(lines[index + 1])
            if file_match and size_match:
                size = size_match.group(1).replace(" ", "")
                unit = size_match.group(2).upper()
                formatted.append(f"附件：{file_match.group(1)}（{size}{unit}）")
                index += 2
                continue
        formatted.append(current)
        index += 1
    return formatted


def _should_merge_text_blocks(previous_text: str, current_text: str) -> bool:
    previous = _normalize_spacing(_last_nonempty_line(previous_text))
    current = _normalize_spacing(_first_nonempty_line(current_text))
    if not previous or not current:
        return False
    if _is_ordered_marker_only(current):
        return False
    if _is_ordered_marker_only(previous):
        return True
    if _is_closing_fragment(current):
        return True
    if (
        _line_contains_url(previous)
        and URL_CONTINUATION_RE.match(current)
        and not URL_START_RE.match(current)
    ):
        return True
    if (
        _line_contains_url(previous_text)
        and URL_CONTINUATION_RE.match(previous)
        and URL_CONTINUATION_RE.match(current)
        and not URL_START_RE.match(current)
    ):
        return True
    if _line_contains_url(previous) and current.startswith(CLOSING_BRACKETS):
        return True
    if URL_START_RE.match(current) and previous.endswith(("(", "（")):
        return True
    if not _should_join_with_previous(previous, current):
        return False
    if _looks_like_wrapped_tail(previous, current):
        return True
    if previous.endswith(CLOSING_BRACKETS) or _has_empty_parentheses(previous):
        return False
    return len(previous) >= 12 and len(current) >= 12


def _last_nonempty_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _first_nonempty_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


def _merge_url_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if (
            merged
            and _line_contains_url(merged[-1])
            and URL_CONTINUATION_RE.match(line)
            and not URL_START_RE.match(line)
        ):
            merged[-1] = merged[-1].rstrip() + line.strip()
            continue
        merged.append(line)
    return merged


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if merged and _should_join_with_previous(merged[-1], line):
            merged[-1] = _join_lines(merged[-1], line)
            continue
        merged.append(line)
    return merged


def _should_join_with_previous(previous: str, current: str) -> bool:
    if not previous or not current:
        return False
    if _is_ordered_marker_only(current):
        return False
    if _is_ordered_marker_only(previous):
        return True
    if _is_closing_fragment(current):
        return True
    if _line_contains_url(previous) and current.startswith(CLOSING_BRACKETS):
        return True
    if (
        _line_contains_url(previous)
        and re.match(r"^[\u4e00-\u9fff]", current)
        and _url_is_at_line_boundary(previous)
    ):
        return False
    if URL_START_RE.match(_normalize_spacing(current)) and previous.endswith(("(", "（")):
        return True
    if URL_START_RE.match(_normalize_spacing(current)) and _has_empty_parentheses(previous):
        return True
    if HORIZONTAL_RULE_RE.match(previous):
        return False
    if _is_numeric_line(previous) and _is_numeric_line(current):
        return False
    if _looks_like_route_line(previous):
        return False
    if _starts_new_block(current):
        return False
    if previous.endswith(CLOSING_BRACKETS):
        return False
    if _has_empty_parentheses(previous):
        return False
    if _looks_like_metadata_line(previous) or _looks_like_metadata_line(current):
        return False
    if _looks_like_heading(previous) or _looks_like_heading(current):
        return False
    if previous[-1] in "。！？!?；;：:":
        return False
    return True


def _starts_new_block(line: str) -> bool:
    normalized = _normalize_spacing(line)
    return bool(
        URL_START_RE.match(normalized)
        or BULLET_RE.match(normalized)
        or HORIZONTAL_RULE_RE.match(normalized)
        or CLOSING_PHRASE_RE.match(normalized)
        or _is_ordered_marker_only(normalized)
        or _is_note_section_heading(normalized)
        or DATE_LINE_RE.match(normalized)
        or TOP_LINE_RE.match(normalized)
        or LABEL_START_RE.match(normalized)
        or _format_ordered_line(normalized)
        or CHINESE_SECTION_RE.match(normalized)
    )


def _looks_like_metadata_line(line: str) -> bool:
    normalized = _normalize_spacing(line)
    return bool(LABEL_START_RE.match(normalized))


def _line_contains_url(line: str) -> bool:
    return "http://" in line or "https://" in line or line.startswith("www.")


def _url_is_at_line_boundary(line: str) -> bool:
    normalized = _normalize_spacing(line)
    return bool(URL_ONLY_RE.match(normalized) or URL_END_RE.search(normalized))


def _join_lines(previous: str, current: str) -> str:
    if URL_START_RE.match(_normalize_spacing(current)) and _has_empty_parentheses(previous):
        return _fill_empty_parentheses(previous, current.strip())
    if _line_contains_url(previous):
        return previous.rstrip() + current.strip()
    if _ends_with_ascii(previous) and _starts_with_ascii(current):
        return previous.rstrip() + " " + current.lstrip()
    return previous.rstrip() + current.lstrip()


def _is_ordered_marker_only(line: str) -> bool:
    return bool(ORDERED_MARKER_ONLY_RE.match(_normalize_spacing(line)))


def _is_note_section_heading(line: str) -> bool:
    return _normalize_spacing(line) in NOTE_SECTION_HEADINGS


def _is_closing_fragment(text: str) -> bool:
    normalized = _normalize_spacing(text)
    return normalized in CLOSING_BRACKETS


def _looks_like_wrapped_tail(previous: str, current: str) -> bool:
    normalized = _normalize_spacing(current)
    if len(normalized) > 12:
        return False
    if _starts_new_block(normalized):
        return False
    if _looks_like_metadata_line(normalized):
        return False
    if not _ends_with_open_text(previous):
        return False
    return _starts_with_continuation_text(normalized)


def _ends_with_open_text(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]$", text))


def _starts_with_continuation_text(text: str) -> bool:
    if not text:
        return False
    return bool(re.match(r"^[\u4e00-\u9fffA-Za-z0-9]", text))


def _is_numeric_line(text: str) -> bool:
    return bool(re.fullmatch(r"\d+", _normalize_spacing(text)))


def _looks_like_route_line(text: str) -> bool:
    return any(marker in text for marker in ("->", "-》", "→"))


def _attach_url_blocks_to_empty_parentheses(blocks: list[str]) -> list[str]:
    attached: list[str] = []
    pending_empty_parentheses: list[int] = []

    for block in blocks:
        stripped = block.strip()
        if _is_single_url_line(stripped) and pending_empty_parentheses:
            target_index = pending_empty_parentheses.pop(0)
            attached[target_index] = _fill_empty_parentheses(
                attached[target_index],
                stripped,
            )
            if _has_empty_parentheses(attached[target_index]):
                pending_empty_parentheses.insert(0, target_index)
            continue

        attached.append(block)
        if _has_empty_parentheses(block):
            pending_empty_parentheses.append(len(attached) - 1)

    return attached


def _merge_adjacent_formatted_blocks(blocks: list[str]) -> list[str]:
    merged: list[str] = []
    for block in blocks:
        if merged and _should_merge_formatted_blocks(merged[-1], block):
            merged[-1] = _join_formatted_blocks(merged[-1], block)
            continue
        merged.append(block)
    return merged


def _should_merge_formatted_blocks(previous_block: str, current_block: str) -> bool:
    previous = _last_nonempty_line(previous_block)
    current = _first_nonempty_line(current_block)
    if not previous or not current:
        return False
    if _is_structural_formatted_line(previous) or _is_structural_formatted_line(current):
        return False
    if not _should_join_with_previous(previous, current):
        return False
    return _looks_like_wrapped_tail(previous, current) or (
        len(previous) >= 12 and len(current) >= 12
    )


def _is_structural_formatted_line(line: str) -> bool:
    normalized = _normalize_spacing(line)
    return bool(
        normalized.startswith(("# ", "## ", "|", "[图片占位符", "![图片：", "附件："))
        or HORIZONTAL_RULE_RE.match(normalized)
        or _format_ordered_line(normalized)
        or BULLET_RE.match(normalized)
        or DATE_LINE_RE.match(normalized)
        or LABEL_START_RE.match(normalized)
    )


def _join_formatted_blocks(previous_block: str, current_block: str) -> str:
    previous_lines = previous_block.splitlines()
    current_lines = current_block.splitlines()
    first_current_index = next(
        (index for index, line in enumerate(current_lines) if line.strip()),
        None,
    )
    if first_current_index is None:
        return previous_block

    last_previous_index = next(
        (
            index
            for index in range(len(previous_lines) - 1, -1, -1)
            if previous_lines[index].strip()
        ),
        None,
    )
    if last_previous_index is None:
        return current_block

    previous_lines[last_previous_index] = _join_lines(
        previous_lines[last_previous_index],
        current_lines[first_current_index],
    )
    remaining_current = current_lines[first_current_index + 1 :]
    return "\n".join(previous_lines + remaining_current)


def _attach_urls_to_empty_parentheses(lines: list[str]) -> list[str]:
    attached: list[str] = []
    pending_empty_parentheses: list[int] = []

    for line in lines:
        if _is_single_url_line(line) and pending_empty_parentheses:
            target_index = pending_empty_parentheses.pop(0)
            attached[target_index] = _fill_empty_parentheses(
                attached[target_index],
                line.strip(),
            )
            if _has_empty_parentheses(attached[target_index]):
                pending_empty_parentheses.insert(0, target_index)
            continue

        attached.append(line)
        if _has_empty_parentheses(line):
            pending_empty_parentheses.append(len(attached) - 1)

    return attached


def _is_single_url_line(text: str) -> bool:
    return bool(URL_START_RE.match(text)) and "\n" not in text


def _has_empty_parentheses(text: str) -> bool:
    return bool(EMPTY_PARENTHESES_RE.search(text))


def _fill_empty_parentheses(text: str, url: str) -> str:
    return EMPTY_PARENTHESES_RE.sub(
        lambda match: f"{match.group(1)}{url}{match.group(2)}",
        text,
        count=1,
    )


def _ends_with_ascii(text: str) -> bool:
    return bool(text) and text[-1].isascii() and text[-1].isalnum()


def _starts_with_ascii(text: str) -> bool:
    return bool(text) and text[0].isascii() and text[0].isalnum()
