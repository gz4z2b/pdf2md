from pathlib import Path

from pdf2md.markdown_writer import (
    BLANK_PAGE_PLACEHOLDER,
    build_markdown,
    image_placeholder,
    write_markdown_file,
)
from pdf2md.pdf_reader import PdfContent, PdfDocument, PdfImage, PdfPage


def test_build_markdown_writes_text_images_and_blank_placeholder_without_page_heading():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="Hello PDF",
                image_count=2,
                contents=(PdfContent(kind="text", text="Hello PDF"),),
            ),
            PdfPage(number=2, text="", image_count=0),
        ),
    )

    markdown = build_markdown(document)

    assert markdown.startswith("# demo\n")
    assert "## 第 1 页" not in markdown
    assert "Hello PDF" in markdown
    assert image_placeholder(1) in markdown
    assert image_placeholder(2) in markdown
    assert "[图片占位符：第 3 张图片]" not in markdown
    assert "## 第 2 页" not in markdown
    assert BLANK_PAGE_PLACEHOLDER in markdown
    assert markdown.endswith("\n")


def test_build_markdown_formats_headings_ordered_lists_and_tables():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="移动广告业务"),
                    PdfContent(kind="text", text="1、第一项\n2、第二项"),
                    PdfContent(
                        kind="table",
                        table_rows=(
                            ("年份", "历程及荣誉"),
                            ("2012 年", "\uf0d8 心理 FM 获奖\n\uf0d8 注册用户增长"),
                        ),
                    ),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "## 移动广告业务" in markdown
    assert "1. 第一项" in markdown
    assert "2. 第二项" in markdown
    assert "| 年份 | 历程及荣誉 |" in markdown
    assert "| --- | --- |" in markdown
    assert "| 2012 年 | - 心理 FM 获奖<br>- 注册用户增长 |" in markdown


def test_build_markdown_keeps_note_section_heading_and_pairs_number_markers():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="今天完成"),
                    PdfContent(kind="text", text="1."),
                    PdfContent(kind="text", text="用户管理"),
                    PdfContent(kind="text", text="2."),
                    PdfContent(kind="text", text="用户注册"),
                    PdfContent(kind="text", text="nodejs会一个框架的入门"),
                    PdfContent(kind="text", text="APP注册加来源"),
                    PdfContent(kind="text", text="重要不紧急"),
                    PdfContent(kind="text", text="1.lfs完成一次"),
                    PdfContent(kind="text", text="学习vimscript"),
                    PdfContent(kind="text", text="项目添加企业项目判断"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "## 今天完成" in markdown
    assert "1. 用户管理" in markdown
    assert "2. 用户注册" in markdown
    assert "1. 用户管理\n2. 用户注册" in markdown
    assert "今天完成1." not in markdown
    assert "用户管理2." not in markdown
    assert "nodejs会一个框架的入门APP注册加来源" in markdown
    assert "## 重要不紧急" in markdown
    assert "APP注册加来源重要不紧急" not in markdown


def test_build_markdown_merges_wrapped_text_urls_and_numbers_images_globally():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=2,
                contents=(
                    PdfContent(kind="text", text="这是一个很长\n的句子"),
                    PdfContent(kind="text", text="https://example.com/path?stu\ndy_style_id=feeds&isappinstall\ned=0"),
                ),
            ),
            PdfPage(number=2, text="", image_count=1),
        ),
    )

    markdown = build_markdown(document)

    assert "这是一个很长的句子" in markdown
    assert "https://example.com/path?study_style_id=feeds&isappinstalled=0" in markdown
    assert "[图片占位符：第 1 张图片]" in markdown
    assert "[图片占位符：第 2 张图片]" in markdown
    assert "[图片占位符：第 3 张图片]" in markdown


def test_build_markdown_merges_wrapped_text_across_pdf_blocks():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="这是 PDF 提取时被拆开的第一段内容"),
                    PdfContent(kind="text", text="后半段应该接在同一个段落里"),
                    PdfContent(kind="text", text="https://example.com/path?stu"),
                    PdfContent(kind="text", text="dy_style_id=feeds&isappinstall"),
                    PdfContent(kind="text", text="ed=0"),
                    PdfContent(kind="text", text="「云+物娱」（"),
                    PdfContent(kind="text", text="http://www.yunjiawuyu.com"),
                    PdfContent(kind="text", text="）是在线抓娃娃开放平台"),
                    PdfContent(kind="text", text="拉勾主页：(\n)，搜狐新闻：（\n）"),
                    PdfContent(kind="text", text="https://www.lagou.com/gongsi/65572.html"),
                    PdfContent(kind="text", text="http://www.sohu.com/a/205805365_439726"),
                    PdfContent(kind="text", text="获3500万元A轮融资，让线下娃娃机回归线上（\n），或百度搜索“云+物娱”，获"),
                    PdfContent(kind="text", text="http://www.sohu.com/a/205805365_439726"),
                    PdfContent(kind="text", text="取相关信息。"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "这是 PDF 提取时被拆开的第一段内容后半段应该接在同一个段落里" in markdown
    assert "https://example.com/path?study_style_id=feeds&isappinstalled=0" in markdown
    assert "「云+物娱」（http://www.yunjiawuyu.com）是在线抓娃娃开放平台" in markdown
    assert "拉勾主页：(https://www.lagou.com/gongsi/65572.html)" in markdown
    assert "搜狐新闻：（http://www.sohu.com/a/205805365_439726）" in markdown
    assert "65572.htmlhttp://www.sohu.com" not in markdown
    assert "获3500万元A轮融资，让线下娃娃机回归线上（http://www.sohu.com/a/205805365_439726），或百度搜索“云+物娱”，获取相关信息。" in markdown


def test_build_markdown_avoids_common_false_headings_and_splits_inline_lists():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="推荐职位：PHP高级工程师"),
                    PdfContent(kind="text", text="ed=0"),
                    PdfContent(kind="text", text="Navi Consulting"),
                    PdfContent(kind="text", text="28号去兵马俑-》秦皇陵-》华清池"),
                    PdfContent(kind="text", text="标准餐补"),
                    PdfContent(kind="text", text="职位要求：(1) 熟悉 Python；(2) 熟悉 SQL；(3) 沟通好"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "## 推荐职位：PHP高级工程师" not in markdown
    assert "## ed=0" not in markdown
    assert "## Navi Consulting" not in markdown
    assert "## 28号去兵马俑-》秦皇陵-》华清池" not in markdown
    assert "## 标准餐补" not in markdown
    assert "1. 熟悉 Python" in markdown
    assert "2. 熟悉 SQL" in markdown
    assert "3. 沟通好" in markdown


def test_build_markdown_preserves_structural_lines_and_merges_short_wraps():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="27号中午到，去大雁塔\n28号去兵马俑\n29号华山"),
                    PdfContent(kind="text", text="整个社会正在迅速拉开顶尖水平和二流水"),
                    PdfContent(kind="text", text="平的差距。"),
                    PdfContent(kind="text", text="----------------------------------------------------------"),
                    PdfContent(kind="text", text="您好！我们诚挚邀请您参加面试"),
                    PdfContent(kind="text", text="联系电话：13660486072；020-85656719公司地址： 广州市天河区"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "27号中午到，去大雁塔28号" not in markdown
    assert "27号中午到，去大雁塔\n28号去兵马俑\n29号华山" in markdown
    assert "顶尖水平和二流水平的差距。" in markdown
    assert "----------------------------------------------------------您好" not in markdown
    assert "----------------------------------------------------------\n\n您好！我们诚挚邀请您参加面试" in markdown
    assert "联系电话：13660486072；020-85656719\n公司地址： 广州市天河区" in markdown


def test_build_markdown_formats_rankings_attachments_and_url_notes():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="Top.1 《微信小程序大全（建议收藏）\n》"),
                    PdfContent(kind="text", text="上一段正文。Top.2 《小程序想要什么？\n》"),
                    PdfContent(kind="text", text="壹心理简介.pdf\n363. 64KB"),
                    PdfContent(kind="text", text="https://servercpu.en.alibaba.com/原有公司"),
                    PdfContent(kind="text", text="http://example.com/home.html新的线上平台"),
                    PdfContent(kind="text", text="联系方式：15019411747联系人:李慧"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "1. 《微信小程序大全（建议收藏）》" in markdown
    assert "上一段正文。\n2. 《小程序想要什么？》" in markdown
    assert "附件：壹心理简介.pdf（363.64KB）" in markdown
    assert "https://servercpu.en.alibaba.com/\n原有公司" in markdown
    assert "http://example.com/home.html\n新的线上平台" in markdown
    assert "## 新的线上平台" not in markdown
    assert "联系方式：15019411747\n联系人:李慧" in markdown


def test_build_markdown_keeps_closing_phrases_separate_and_merges_list_continuation():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="2. 熟悉\nnginx+node.js和nginx+php的web后端服务开发经验"),
                    PdfContent(kind="text", text="如有任何问题，请随时联系我"),
                    PdfContent(kind="text", text="祝面试顺利~"),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "2. 熟悉nginx+node.js和nginx+php的web后端服务开发经验" in markdown
    assert "联系我祝面试顺利" not in markdown
    assert "如有任何问题，请随时联系我\n\n祝面试顺利~" in markdown


def test_build_markdown_formats_orphan_bullet_markers_and_continuing_tables():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(kind="text", text="\uf075\n壹心理理念\nI SEE YOU"),
                    PdfContent(
                        kind="table",
                        table_rows=(
                            ("年份", "历程及荣誉"),
                            ("2016 年", "获奖 A"),
                        ),
                    ),
                    PdfContent(
                        kind="table",
                        table_rows=(
                            ("年份", "历程及荣誉"),
                            ("", "获奖 B"),
                            ("2017 年", "获奖 C"),
                        ),
                    ),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert "\uf075" not in markdown
    assert "## 壹心理理念" in markdown
    assert markdown.count("| 年份 | 历程及荣誉 |") == 1
    assert "| 2016 年 | 获奖 A |" in markdown
    assert "|  | 获奖 B |" in markdown
    assert "| 2017 年 | 获奖 C |" in markdown


def test_build_markdown_continues_table_across_pages_without_blank_line():
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=0,
                contents=(
                    PdfContent(
                        kind="table",
                        table_rows=(("年份", "历程"), ("2016 年", "获奖 A")),
                    ),
                ),
            ),
            PdfPage(
                number=2,
                text="",
                image_count=0,
                contents=(
                    PdfContent(
                        kind="table",
                        table_rows=(("年份", "历程"), ("2017 年", "获奖 B")),
                    ),
                ),
            ),
        ),
    )

    markdown = build_markdown(document)

    assert markdown.count("| 年份 | 历程 |") == 1
    assert "| 2016 年 | 获奖 A |\n| 2017 年 | 获奖 B |" in markdown


def test_write_markdown_file_skips_existing_file_without_overwrite(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(PdfPage(number=1, text="New content", image_count=0),),
    )
    output_path = tmp_path / "demo.md"
    output_path.write_text("old content", encoding="utf-8")

    written = write_markdown_file(document, output_path, overwrite=False)

    assert written is False
    assert output_path.read_text(encoding="utf-8") == "old content"


def test_write_markdown_file_overwrites_when_requested(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(PdfPage(number=1, text="New content", image_count=0),),
    )
    output_path = tmp_path / "demo.md"
    output_path.write_text("old content", encoding="utf-8")

    written = write_markdown_file(document, output_path, overwrite=True)

    assert written is True
    assert "New content" in output_path.read_text(encoding="utf-8")


def test_write_markdown_file_exports_images_to_sources_and_links_them(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/nested/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="带图片的 PDF",
                image_count=1,
                images=(
                    PdfImage(
                        page_number=1,
                        index=1,
                        extension="png",
                        data=b"image-bytes",
                    ),
                ),
            ),
        ),
    )
    output_path = tmp_path / "output" / "nested" / "demo.md"
    resources_root = tmp_path / "output" / "sources"

    written = write_markdown_file(
        document,
        output_path,
        overwrite=True,
        resources_dir=resources_root / "nested" / "demo",
    )

    image_path = resources_root / "nested" / "demo" / "page-001-image-001.png"
    markdown = output_path.read_text(encoding="utf-8")
    assert written is True
    assert image_path.read_bytes() == b"image-bytes"
    assert "![图片：第 1 张图片](../sources/nested/demo/page-001-image-001.png)" in markdown
    assert "PDF![图片" not in markdown
    assert "\n\n![图片：第 1 张图片]" in markdown
    assert image_placeholder(1) not in markdown


def test_write_markdown_file_keeps_placeholder_when_image_data_is_missing(tmp_path):
    document = PdfDocument(
        source_path=Path("origin/demo.pdf"),
        title="demo",
        pages=(
            PdfPage(
                number=1,
                text="",
                image_count=1,
                images=(
                    PdfImage(page_number=1, index=1, extension="bin", data=b""),
                ),
            ),
        ),
    )
    output_path = tmp_path / "output" / "demo.md"

    written = write_markdown_file(
        document,
        output_path,
        overwrite=True,
        resources_dir=tmp_path / "output" / "sources" / "demo",
    )

    assert written is True
    assert image_placeholder(1) in output_path.read_text(encoding="utf-8")
    assert not (tmp_path / "output" / "sources" / "demo").exists()
