from pathlib import Path

from .pdf_reader import PdfDocument


BLANK_PAGE_PLACEHOLDER = "[本页没有可识别文字]"


def image_placeholder(page_number: int, image_index: int) -> str:
    return f"[图片占位符：第 {page_number} 页第 {image_index} 张图片]"


def build_markdown(document: PdfDocument) -> str:
    lines = [f"# {document.title}"]

    for page in document.pages:
        lines.extend(["", f"## 第 {page.number} 页"])

        blocks: list[str] = []
        if page.text:
            blocks.append(page.text)

        for image_index in range(1, page.image_count + 1):
            blocks.append(image_placeholder(page.number, image_index))

        if not blocks:
            blocks.append(BLANK_PAGE_PLACEHOLDER)

        for block in blocks:
            lines.extend(["", block.rstrip()])

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_file(
    document: PdfDocument,
    output_path: Path,
    *,
    overwrite: bool = False,
) -> bool:
    target_path = Path(output_path)
    if target_path.exists() and not overwrite:
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(build_markdown(document), encoding="utf-8")
    return True
