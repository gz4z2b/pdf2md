# 批量 PDF 转 Markdown

## 功能用途

本功能用于把 `origin` 目录以及子目录里的 PDF 文件批量转换成 Markdown 文档。如果 `origin` 里已经有 Markdown 文件，会直接复制到 `output` 对应位置。PDF 中能提取到的图片会导出到 `output/sources`。

适合下面这种场景：

1. 用户有很多 PDF 文档。
2. 用户也可能已经有一些 Markdown 文档，需要一起整理到输出目录。
3. 用户想把这些文档变成更容易阅读、复制和二次编辑的 Markdown。
4. 用户不想一个文件一个文件手动转换或复制。
5. 用户希望 PDF 中的图片也能作为独立文件保留下来。

## 使用入口

用户执行：

```bash
bash scripts/convert.sh
```

脚本会自动扫描 `origin` 目录，不需要用户记复杂命令。

## 输入目录

默认输入目录：

```text
origin/
```

规则：

1. 处理 `.pdf` 和 `.md` 文件。
2. 会递归处理子目录。
3. 文件后缀大小写不敏感，`.pdf`、`.PDF`、`.md`、`.MD` 都应识别。
4. 非 PDF、非 Markdown 文件会被跳过。

示例：

```text
origin/
├── a.pdf
├── b.PDF
├── interview.note.pdf
├── c.md
└── sub/
    ├── d.pdf
    └── e.MD
```

## 输出目录

默认输出目录：

```text
output/
```

输出时会保留原来的子目录结构：

```text
output/
├── a.md
├── b.md
├── interview.md
├── c.md
├── sources/
│   ├── a/
│   │   └── page-001-image-001.png
│   ├── interview/
│   │   └── page-001-image-001.png
│   └── sub/
│       └── d/
│           └── page-001-image-001.png
└── sub/
    ├── d.md
    └── e.MD
```

`sources` 是资源目录，保存从 PDF 中导出的图片。普通 Markdown 文件仍放在原来的相对目录里。文件名末尾如果有 `.note`，输出时会去掉，例如 `interview.note.pdf` 会输出为 `interview.md`。

## 转换规则

| PDF 内容 | Markdown 输出规则 |
| --- | --- |
| 普通文字 | 输出为 Markdown 段落 |
| 页面分隔 | 不额外写入页码标题 |
| 明显标题 | 单独一行、较像章节名且没有标点结尾时，尽量转换为 Markdown 标题 |
| 列表文字 | 尽量转换为 Markdown 有序列表或无序列表 |
| 表格内容 | 能识别行列结构时，尽量转换为 Markdown 表格 |
| 图片 | 尽量导出到 `output/sources`，并在 Markdown 中写入图片引用；无法导出时保留占位符 |
| 空白页 | 输出空白页提示 |
| Markdown 源文件 | 不改内容，直接复制到输出目录 |

图片引用示例：

```markdown
![图片：第 1 张图片](sources/demo/page-001-image-001.png)
```

图片无法导出时，会退回占位符：

```markdown
[图片占位符：第 1 张图片]
```

空白页提示示例：

```markdown
[本页没有可识别文字]
```

## 参数说明

v1.0.0 默认不要求用户填写参数。代码实现时可以预留下面这些参数，方便后续扩展。

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--input-dir` | `origin` | PDF 和 Markdown 输入目录 |
| `--output-dir` | `output` | Markdown 输出目录 |
| `--overwrite` | 默认行为 | 替换已经存在的 Markdown 文件 |
| `--skip-existing` | `false` | 如果 Markdown 文件已存在，则跳过该文件 |
| `--log-level` | `INFO` | 日志详细程度 |

## 返回结果

一键脚本执行结束后，终端应展示汇总信息：

```text
完成：成功 3 个，失败 0 个，输出目录：output
```

如果有失败文件，应展示失败列表：

```text
完成：成功 2 个，失败 1 个
失败文件：
- origin/bad.pdf：文件无法读取
```

## 异常处理

| 情况 | 处理方式 |
| --- | --- |
| `origin` 不存在 | 自动创建目录，并提示用户放入 PDF 或 Markdown 后重新执行 |
| 没有 PDF 或 Markdown 文件 | 输出提示，不报错 |
| 只有 Markdown 文件 | 直接复制 Markdown，不报错 |
| PDF 损坏 | 记录失败原因，继续转换其他文件 |
| 输出目录不存在 | 自动创建 |
| 输出文件已存在 | 默认直接替换；用户启用 `--skip-existing` 后才跳过 |
| PDF 图片可读取 | 导出到 `output/sources/源文件相对路径去后缀/` |
| PDF 图片无法读取 | Markdown 中保留图片占位符，避免内容位置完全丢失 |
| 旧输出文件带 `.note` | 转换同一个源文件时，会清理旧的 `.note.md` 和旧的 `.note` 图片目录 |

## v1.0.0 不做的内容

下面内容不属于 v1.0.0 范围：

1. 不保证复杂表格 100% 转成标准 Markdown 表格。
2. 不处理扫描版 PDF 的 OCR 识别。
3. 不提供网页界面。
4. 不提供批量上传下载服务。
5. 不提取 PDF 中的视频、音频等复杂嵌入对象；当前多媒体导出主要指图片。

这些能力可以放到后续版本继续开发。
