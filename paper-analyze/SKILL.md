---
name: paper-analyze
description: 使用 Kimi 论文数据库或公开来源深度分析论文/PDF/网页，经 Zotero 笔记插件将 Kimi 撰写的完整笔记导入思源并绑定 Zotero。Use for arXiv IDs, public or local PDFs, project pages, blogs, and webpage analysis.
---

# 单篇深度分析

## 来源与证据

1. arXiv ID/链接：调用 Kimi arxiv `download_paper`，需要时查询状态，再 `read_paper`。不得改用直接 arXiv 搜索 API。
2. 其他公开 PDF、本地 PDF、项目页、博客和普通网页：使用 `scripts/resolve_source.py` 识别并保存到系统临时目录。网页正文不完整时使用当前 Agent 的网页能力。
3. 只有 arXiv 来源才写 `arxiv_id`。其他来源保留原始 URL，不伪造会议、作者、日期或实验结论。全文不可得时只分析可见证据并注明范围。

## 生成完整内容

1. 创建临时工作目录 `WORK`，读取仓库 `config.yaml`。
2. 需要模板时运行：

```bash
python "$SKILL_DIR/scripts/generate_note.py" \
  --title "<title>" --authors "<authors>" --domain "<domain>" \
  --source-type "<type>" --source-url "<url>" --document-id "<stable-id>" \
  --paper-id "<arxiv-id-only-for-arxiv>" --published-date "<date>" \
  --output "$WORK/analysis.md"
```

3. Kimi 阅读全文后替换全部占位符。区分作者主张、论文证据和 Kimi 推断；保留“我的笔记”之外的完整分析结构。
4. 图片调用 `extract-paper-images`，正文只使用返回的 `assets/...` 标准 Markdown 链接。
5. 构造 `$WORK/paper.json`：`{"top_papers":[paper]}`。paper 包含标题、作者、摘要、日期、URL、PDF URL、arxiv_id（如适用）、`analysis_markdown` 和 `assets`。

## 导入与验证

```bash
python "$REPO_ROOT/start-my-day/scripts/research_workflow.py" \
  --config "$REPO_ROOT/config.yaml" \
  --ranked "$WORK/paper.json" \
  --target-date "YYYY-MM-DD" \
  --single
```

脚本先通过 `ensure_papers` 创建/复用 Zotero 条目及 `Zotero/<论文>/Note`，再按 Kimi 的冲突策略调用 `write_documents` 原样写入笔记和 PaperGraph。已有手工 Note 默认保留；只有用户明确要求时才使用 `--force`。

返回 Zotero itemKey、论文页和 Note 的 `siyuan://blocks/` 链接、写入/保留状态及证据缺失范围。可在 Zotero 插件中继续编辑或回传 Note。
