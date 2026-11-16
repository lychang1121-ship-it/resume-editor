# 简历内容 JSON 规范与字段映射

本文件供执行 skill 的模型在整理简历内容时参考。`scripts/build_editor.py` 只接受本规范描述的 JSON，并负责把它渲染成模板中的 `<main id="resume">`。

## 完整字段

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 姓名，作为 `<h1>` 与文件标题 |
| `role` | string[] | 否 | 定位/职能，1–2 行，用 `<br>` 换行 |
| `meta` | string[] | 否 | 电话、邮箱、城市、出差意愿等，逐行 |
| `kicker` | string | 否 | 顶部英文小标题，如 `B2B PRODUCT · SOLUTION · GROWTH` |
| `summary` | string[] | 否 | 1–2 段概述，每段一个 `<p class="summary">` |
| `numbers` | object[] | 否 | 最多 4 张指标卡：`value` / `unit` / `label` / `note` |
| `side_blocks` | object[] | 否 | 侧栏分区：`title` + `chips`（标签块）或 `lines`（文本块） |
| `sections` | object[] | 否 | 主栏章节：`title` / `type` / `items` |

### numbers

```json
{"value": "30", "unit": "%", "label": "流程效率提升", "note": "上线周期由 6 周缩短至 4 周"}
```

`value` 放数字或短文本，`unit` 放 `%` / `万元` / `个` 等单位。只使用简历原文中出现的量化结果，凑不满 4 张就少放，不要编造。

### side_blocks

```json
{"title": "优势标签", "chips": ["需求分析", "方案设计", "跨团队协作"]}
{"title": "工具与语言", "lines": ["产品：Figma · Axure · Jira", "数据：SQL · Excel"]}
```

有 `chips` 时渲染成可增删的标签块；否则 `lines` 逐行渲染成 `<p>`。建议顺序：优势标签 → 专业基础 → 工具与语言 → 求职方向。原简历没有对应信息时，直接省略该块，不要写「暂无」。

### sections

`type` 取值：`timeline`（工作/实习条目）、`project`（项目条目）、`edu`（教育条目）。别名 `work` / `internship` → timeline，`education` → edu。

`timeline` 的 item：

```json
{
  "when": ["2023.04", "至今"],
  "title": "高级产品经理｜示例科技有限公司",
  "org": "企业服务事业部｜B 端 SaaS 产品线",
  "bullets": [
    {"label": "需求与规划", "text": "走访 30 家以上客户，主导季度路线图。"},
    "纯文本要点（无小标题时可写成字符串）"
  ]
}
```

`bullets[].label` 取自原文的小标题或加粗词，会渲染成 `<b>标签：</b>`；没有小标题就写纯字符串，或省略 label 只给 `text`。

`project` 的 item：`{"title": "...", "text": "..."}`。

`edu` 的 item：`{"when": ["2017.09", "2021.06"], "title": "...", "org": "...", "small": "..."}`。

## 映射规则

1. **只搬运事实**：姓名、公司、学校、时间、数字、成果一律沿用原文，不推测、不补齐、不美化数字。原文没有的信息留空或省略整个字段。
2. **章节顺序**：工作经历 → 项目/专项实践 → 教育背景 → 实习/其他，按原文实际章节调整；`type` 按内容形态选择，不要把所有内容都塞进 `timeline`。
3. **指标卡**：从原文的量化业绩里挑最多 4 个最有代表性的，`note` 用来写限定语（如「参与」「在跟进」），避免夸大。
4. **概述**：用原文事实压缩成 1–2 段，不新增评价性形容词；原文没有概述时可以省略 `summary`。
5. **长度**：A4 单页版式很紧，中文每条 bullet 建议 ≤ 60 字，全篇工作经历条目 ≤ 3 个、每条目 ≤ 6 条要点。内容过多时优先保留最近一段经历的要点，其余精简为一行。
6. **侧栏标签**：取原文技能词、工具名、方向词，8 个以内。
7. **照片**：不从简历里猜测照片；默认使用内嵌 SVG 占位图，由用户后续在编辑器里点「更换照片」替换。若用户另行提供照片文件，生成时传 `--photo`。

## 最小可用示例

```json
{
  "name": "林亦舟",
  "role": ["B 端产品", "解决方案与增长"],
  "meta": ["138-0000-0000", "hello@example.com", "现居上海"],
  "kicker": "B2B PRODUCT · SOLUTION · GROWTH",
  "summary": ["5 年 B 端产品与解决方案经验，负责从需求调研到交付复盘的全流程。"],
  "numbers": [
    {"value": "30", "unit": "%", "label": "流程效率提升", "note": "上线周期由 6 周缩短至 4 周"}
  ],
  "side_blocks": [
    {"title": "优势标签", "chips": ["需求分析", "方案设计", "数据驱动"]},
    {"title": "专业基础", "lines": ["计算机科学与技术", "数据结构 · 数据库系统"]}
  ],
  "sections": [
    {
      "title": "工作经历", "type": "timeline",
      "items": [{
        "when": ["2023.04", "至今"],
        "title": "高级产品经理｜示例科技有限公司",
        "org": "企业服务事业部",
        "bullets": [{"label": "需求与规划", "text": "走访 30 家以上客户，主导季度路线图。"}]
      }]
    },
    {
      "title": "教育背景", "type": "edu",
      "items": [{"when": ["2017.09", "2021.06"], "title": "示例大学｜计算机科学与技术 · 本科"}]
    }
  ]
}
```

## 生成后的检查

生成 HTML 后，确认：

- 文件里仍有 `<div class="editor-ui" id="editor">`、`<script>`、`<main class="page" id="resume">`；
- `data-module=` 数量大于 0（模块增删/复制依赖它）；
- 用 Chrome/Edge 打开无报错，且顶部工具栏、局部格式栏可用；
- 生成的 HTML 含真实个人信息，提醒用户不要提交到公开仓库。
