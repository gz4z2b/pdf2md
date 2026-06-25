# pdf 转 Markdown 文档工具

这是一个用 Python 开发的 PDF 批量转 Markdown 工具。

项目目标很简单：把 `origin` 目录以及子目录里的 PDF 文件读取出来，尽量保持原文档的标题、段落、换行和表格等排版，再输出成 `.md` 格式文档。v1.0.0 阶段先处理文字内容；如果 PDF 中出现图片，先在 Markdown 中写入图片占位符，后续版本再处理真实图片导出。

## 使用方式

开发完成后，用户只需要执行一个脚本：

```bash
bash scripts/convert.sh
```

脚本应自动完成下面几件事：

1. 检查本机是否安装了可用的 Python。
2. 创建或复用项目虚拟环境。
3. 安装项目依赖。
4. 扫描 `origin` 目录里的所有 PDF。
5. 把转换后的 Markdown 文件输出到 `output` 目录。目录结构和文件名保持一致。

## 目录说明

```text
pdf2md/
├── README.md                 # 项目总说明和文档索引
├── origin/                   # 用户放 PDF 原文件的目录
├── output/                   # 转换后 Markdown 文件的输出目录
├── scripts/                  # 一键执行脚本目录
├── src/pdf2md/               # Python 源代码目录，开发时创建
├── tests/                    # 测试用例目录，开发时创建
└── docs/                     # 项目文档目录
    ├── rule.md               # 项目规范
    ├── test.md               # 测试规范
    ├── functions/            # 功能说明文档
    └── v1.0.0/               # v1.0.0 版本文档
```

## 项目架构

本项目按“命令入口、业务编排、PDF 解析、Markdown 输出”分层。

| 层级 | 规划模块 | 作用 |
| --- | --- | --- |
| 命令入口层 | `src/pdf2md/cli.py` | 接收命令参数，启动转换任务 |
| 批量任务层 | `src/pdf2md/batch.py` | 扫描 `origin` 目录，批量处理 PDF |
| PDF 解析层 | `src/pdf2md/pdf_reader.py` | 读取 PDF 页面、文字块和图片信息 |
| Markdown 生成层 | `src/pdf2md/markdown_writer.py` | 把解析结果写成 Markdown 文件 |
| 配置层 | `src/pdf2md/config.py` | 管理输入目录、输出目录、日志级别等配置 |
| 异常与日志层 | `src/pdf2md/errors.py`、`src/pdf2md/logger.py` | 统一错误提示和运行日志 |

### 技术栈

| 类型 | 技术 | 用途 |
| --- | --- | --- |
| 开发语言 | Python 3.11+ | 项目主语言 |
| PDF 解析 | PyMuPDF | 读取 PDF 文本块、页面结构和图片信息 |
| 命令行参数 | argparse | 提供简单稳定的命令行入口 |
| 日志 | logging | 输出转换进度、失败原因和调试信息 |
| 测试框架 | pytest | 编写和执行自动化测试 |
| 覆盖率 | pytest-cov | 检查核心代码测试覆盖情况 |
| 测试 PDF 生成 | reportlab | 在测试中生成小型 PDF 样本 |

## 项目规范

请参见: [docs/rule.md](./docs/rule.md)

## 测试规范

请参见：[docs/test.md](./docs/test.md)

## 功能说明

| 功能 | 文档 |
| --- | --- |
| 批量 PDF 转 Markdown | [docs/functions/pdf_batch_convert.md](./docs/functions/pdf_batch_convert.md) |

## 版本文档

| 版本 | 文档 |
| --- | --- |
| v1.0.0 原始需求 | [docs/v1.0.0/需求.md](./docs/v1.0.0/需求.md) |
| v1.0.0 实现方案 | [docs/v1.0.0/实现方案.md](./docs/v1.0.0/实现方案.md) |
| v1.0.0 问题解决 | [docs/v1.0.0/问题解决.md](./docs/v1.0.0/问题解决.md) |
