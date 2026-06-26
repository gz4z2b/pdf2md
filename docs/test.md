# 测试规范

本文档规定 pdf2md 项目的测试方式。后续实现代码时，必须按本文档补充测试。

## 测试目标

v1.0.0 的测试目标是确认下面几件事：

1. 程序能找到 `origin` 目录和子目录中的 PDF 与 Markdown。
2. 每个 PDF 都会输出一个对应的 Markdown 文件。
3. 已有 Markdown 会直接复制到 `output` 对应位置。
4. 输出文件保留原文件的相对目录结构。
5. PDF 文字能被正确读取并写入 Markdown。
6. 遇到 PDF 图片时，会导出图片文件，并在 Markdown 中写入图片引用。
7. 遇到损坏 PDF 或无法读取的 PDF 时，程序不会整体崩溃，而是记录失败原因后继续处理其他文件。
8. 一键脚本能完成环境检查、依赖安装和转换流程。

## 测试工具

| 工具 | 用途 |
| --- | --- |
| `pytest` | 执行测试用例 |
| `pytest-cov` | 查看测试覆盖率 |
| `reportlab` | 生成测试 PDF |
| `tmp_path` | pytest 内置临时目录，避免污染真实 `origin` 和 `output` |

## 测试目录规划

```text
tests/
├── conftest.py
├── fixtures/
├── test_batch.py
├── test_pdf_reader.py
├── test_markdown_writer.py
└── test_cli.py
```

| 文件 | 测试内容 |
| --- | --- |
| `conftest.py` | 公共测试夹具 |
| `test_batch.py` | 目录扫描、批量转换和异常不中断 |
| `test_pdf_reader.py` | PDF 文字、页面和图片信息读取 |
| `test_markdown_writer.py` | Markdown 格式生成和文件写入 |
| `test_cli.py` | 命令行入口和参数 |

## 推荐测试命令

执行全部测试：

```bash
python -m pytest
```

执行测试并查看覆盖率：

```bash
python -m pytest --cov=pdf2md --cov-report=term-missing
```

只执行某个测试文件：

```bash
python -m pytest tests/test_batch.py
```

## 核心用例

| 用例 | 输入 | 预期结果 |
| --- | --- | --- |
| 单个 PDF 转换 | `origin/demo.pdf` | 生成 `output/demo.md` |
| `.note` PDF 转换 | `origin/demo.note.pdf` | 生成 `output/demo.md`，不生成 `output/demo.note.md` |
| 子目录 PDF 转换 | `origin/a/demo.pdf` | 生成 `output/a/demo.md` |
| 多个 PDF 转换 | `origin/a.pdf`、`origin/b.pdf` | 两个文件都转换成功 |
| Markdown 复制 | `origin/a.md` | 生成内容相同的 `output/a.md` |
| 子目录 Markdown 复制 | `origin/a/demo.md` | 生成内容相同的 `output/a/demo.md` |
| 空目录 | `origin` 没有 PDF 或 Markdown | 输出提示，不报错 |
| 图片 PDF | PDF 中有图片 | 图片导出到 `output/sources`，Markdown 中出现图片引用 |
| 空白 PDF | 页面无文字 | Markdown 中出现空白页提示 |
| 损坏 PDF | 无法打开的 PDF | 记录失败，继续处理其他 PDF |

## 测试数据规范

1. 测试 PDF 尽量在测试运行时临时生成。
2. 不要把大体积 PDF 放进仓库。
3. 如果必须放样本 PDF，应放在 `tests/fixtures`，并写明来源和用途。
4. 测试中不要直接读写真实的 `origin` 和 `output` 目录，应使用 `tmp_path` 创建临时目录。

## 验收标准

v1.0.0 开发完成后，至少满足：

1. 所有自动化测试通过。
2. 核心模块测试覆盖率不低于 80%。
3. `scripts/convert.sh` 可以在干净环境中一键执行。
4. 使用一个真实 PDF 手动验证输出结果，确认 Markdown 内容可读。
5. 使用带图片的真实 PDF 手动验证 `output/sources` 中存在图片文件，且 Markdown 链接路径可用。

## 失败处理规范

测试失败时，应按下面顺序排查：

1. 先看失败用例名称，确认是哪个功能失败。
2. 再看错误信息，确认是代码问题、测试数据问题还是环境问题。
3. 如果是代码问题，优先修最小范围的代码。
4. 修复后重新执行相关测试。
5. 如果同一个问题两次调整仍未解决，需要重新列出可能原因和验证办法。
