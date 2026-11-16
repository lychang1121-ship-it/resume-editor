---
name: resume-to-template
description: 把用户提供的简历文件（PDF / DOCX / HTML / Markdown / TXT）改写成 GitHub 风格 A4 单页简历，并生成一个可用「单文件简历修改器」继续编辑的 HTML。当用户上传简历并要求套用模板、换成这个版式、生成可编辑简历、转换成 resume-editor 模板，或提到「简历修改器」「GitHub 风格简历」「用这个编辑器打开我的简历」时，应使用本技能。输出为本地单文件，全程不联网。
agent_created: true
---

# 简历套模板 → 可编辑 HTML

## 概述

把任意简历内容映射到仓库 `index.html` 的两栏 A4 版式，产出一个保留全部编辑能力的 HTML 文件：双击后可以直接改文字、调字体字号、加粗、增删复制模块、导出 PDF。

核心原则：**不让模型改写编辑器代码**。模型只负责把简历整理成结构化 JSON，由 `scripts/build_editor.py` 把内容注入模板，从而保证 50KB 的编辑器逻辑与样式零损坏。

## 触发场景

- 上传简历文件，说「用这个模板改一下」「套成 GitHub 风格」「改成我的简历」「生成可以用 editor 编辑的版本」。
- 已 clone 本仓库，想把自己的简历放进 `index.html` 的版式里。
- 粘贴一大段简历文字，要求排成这个版式。

## 工作流

### 第 1 步：确认输入与模板

取得简历文件路径。确认模板可用：优先通过 `--template` 指向仓库根的 `index.html`（能用到最新版）；若 skill 被独立安装，则使用自带的 `assets/editor-template.html` 快照。

不修改仓库自带的 `index.html`，不覆盖示例内容；始终生成**新文件**。

### 第 2 步：提取简历文本

运行：

```bash
python scripts/extract_resume.py <简历路径> --out <临时文本路径>
```

支持 `.txt` / `.md` / `.html` / `.docx`（纯标准库）与 `.pdf`（自动探测 pypdf、PyPDF2、pdfplumber、PyMuPDF）。结果写到 stdout 或 `--out` 文件。

若 PDF 返回 `PDF_EXTRACTOR_MISSING`，按脚本提示三选一：安装 `pypdf` 后重试、改用 WorkBuddy 的 PDF 能力读出文字、或请用户粘贴简历内容 / 另存为 TXT。图片或扫描件先 OCR，不臆测其中内容。

### 第 3 步：整理成结构化 JSON

读取 `references/schema.md`，把提取出的文本整理成该规范描述的 JSON，写入临时文件（如 `resume_data.json`）。

遵守以下约束：

- 姓名、公司、学校、时间、数字、成果一律沿用原文，不推测、不补齐、不夸大；缺失字段直接省略。
- 指标卡只用原文明确写出的量化结果，凑不满 4 张就少放。
- 按内容形态选择 `timeline` / `project` / `edu`，不把所有内容都塞进时间线。
- 控制篇幅以适配 A4 单页，细节见 `references/schema.md` 的「映射规则」。
- `name` 必填；其它字段可缺省。

### 第 4 步：生成可编辑 HTML

运行：

```bash
python scripts/build_editor.py --data <resume_data.json> --template <仓库根/index.html> --out <姓名>_简历修改器.html
```

可选 `--photo <证件照路径>` 把照片内嵌成 data URI；不传则使用模板自带的 SVG 占位图，用户后续在编辑器里点「更换照片」替换。

脚本会：只替换 `<main id="resume">` 的内容、保留全部 `class` 与 `data-module`、把页面标题设为「姓名｜简历」、按姓名与文件名生成独立的 localStorage 键（避免多份简历互相覆盖自动保存）。

检查输出的模块数大于 0；报「找不到模板」时补 `--template`；报「模板中没有找到 main」说明传成了导出的纯净版简历，需改传编辑器 `index.html`。

### 第 5 步：交付

用 `present_files` 打开生成的 HTML，并告知：

- 用 **Chrome / Edge 双击本地文件**打开，在线预览器可能无法正常保存；
- 顶部工具栏改全局字体字号，拖选文字在「文字格式」行单独改字体/字号/加粗；
- 悬停模块可复制、排序、删除；定稿后点「导出简历 HTML」或「打印 / 存 PDF」；
- 该文件含真实个人信息，**不要提交到公开仓库**。

生成完毕即结束，不主动上传、不联网、不把简历内容发到任何外部服务。

## 硬约束

- 全程本地处理，不发起网络请求，不把简历内容发往第三方。
- 不手写或重写 `index.html`；所有内容注入一律通过 `build_editor.py`。
- 不编造简历事实；原文没有的信息留空。
- 不把生成结果写回仓库目录，除非用户明确指定输出路径。
- 不修改 `assets/editor-template.html` 与仓库示例内容。

## 故障处理

| 现象 | 处理 |
| --- | --- |
| PDF 无文本层 / 缺库 | 按第 2 步降级；扫描件提示 OCR |
| JSON 缺 `name` | 从原文确认姓名，仍无法确定时询问用户 |
| 模板找不到 | 显式传 `--template` 指向仓库 `index.html` |
| 生成后模块数为 0 | 检查 `sections` / `side_blocks` 是否为空，补齐后重新生成 |
| 页面文字超出一页 | 提示在编辑器里调小全局字号，或精简 JSON 要点后重新生成 |

## 资源

- `scripts/extract_resume.py` — 多格式简历文本提取
- `scripts/build_editor.py` — JSON 注入模板并生成可编辑 HTML
- `references/schema.md` — 内容 JSON 规范、字段映射规则、最小示例
- `assets/editor-template.html` — 编辑器模板快照（仓库根 `index.html` 更新后重新复制）
