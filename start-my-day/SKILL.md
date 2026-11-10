---
name: start-my-day
description: 使用 Kimi 论文数据库生成每日推荐，通过 siyuan-plugin-zotero-notes 将论文导入 Zotero，并把 Kimi 撰写的日报与前三篇精读写入思源。Use when the user asks to start the day, run daily paper recommendations, or generate recommendations for a date.
---

# 每日论文推荐

## 职责边界

Kimi 负责搜索、候选去重、评分、摘要、日报和精读。Zotero 插件只负责确保文献/文档存在并原样写入 Kimi 提供的内容。不得调用旧论文搜索 API，不得让插件生成日报或决定冲突策略。

前置条件：Kimi 论文数据库、思源 3.7+、Zotero 10+、Zotero 笔记插件 0.2.0 已启用，插件设置已选择笔记本，队列已开启。外部脚本需要环境变量 `SIYUAN_API_TOKEN`。

## 1. 准备

1. 将本目录记为 `SKILL_DIR`，仓库根目录记为 `REPO_ROOT`，读取 `REPO_ROOT/config.yaml`。
2. 目标日期为参数日期或当前日期。创建系统临时工作目录 `WORK`，所有 CSV/JSON/Markdown 临时文件放在这里。
3. 确认数据源接口：分别读取 arxiv 和 scholar 的 data source desc。搜索接口需要 `file_path`，查询不超过 6 个独立关键词且不要用 OR 拼接。
4. 若用户未要求 `force`，重复执行应复用文献并保留已有内容。

## 2. 使用 Kimi 论文数据库搜索

根据研究兴趣为每个领域选择最有代表性的关键词：

- 近期论文：调用 `arxiv.search_papers`，设置 `date_from/date_to` 为最近 `recent_days` 天、相关 `categories`、合理 `max_results`，CSV 文件名含 `arxiv`。
- 过去一年热门论文：调用 `scholar.scholar_search`，设置 `start_year/end_year`、`sort_by=relevance`、每次最多 50 条，CSV 文件名含 `scholar`。

读取完整 CSV，不使用其他论文搜索服务。某个领域失败时记录并继续，禁止用旧脚本兜底。

运行：

```bash
python "$SKILL_DIR/scripts/rank_papers.py" \
  --input "$WORK"/*.csv \
  --config "$REPO_ROOT/config.yaml" \
  --target-date "YYYY-MM-DD" \
  --top-n 10 \
  --output "$WORK/ranked.json"
```

## 3. Kimi 生成推荐内容

读取 `ranked.json`，在工作 JSON 中为每篇补充 `summary`、`contributions`、`key_results`，并撰写今日概览保存为 `$WORK/overview.md`。内容必须基于标题、摘要和评分，不编造机构、实验数字或结论。

对前三篇：

1. 调用 arxiv `download_paper`，需要时轮询转换状态，再调用 `read_paper` 获取全文。
2. 按 `paper-analyze` 的证据规则撰写完整精读，放入该论文的 `analysis_markdown`。无法取得全文时明确限制，不伪造精读。
3. 需要图片时调用 `extract-paper-images`，把返回的 assets 路径放入该论文 `assets`。

## 4. 两阶段导入

运行：

```bash
python "$SKILL_DIR/scripts/research_workflow.py" \
  --config "$REPO_ROOT/config.yaml" \
  --ranked "$WORK/ranked.json" \
  --overview-file "$WORK/overview.md" \
  --target-date "YYYY-MM-DD" > "$WORK/result.json"
```

脚本先提交 `ensure_papers`，取得每篇 `itemKey/parentDocId/noteDocId`，再生成完整日报和 PaperGraph，按当前文档状态决定写入/跳过/保留并提交 `write_documents`。只有用户明确要求强制刷新时才添加 `--force`。

## 5. 验证与汇报

检查 JSON 结果及必要的思源/Zotero 实际状态：

- 推荐论文均有 Zotero itemKey；失败项明确列出，不能把 partial 说成成功。
- 日报路径正确，链接含 `zotero://select/library/items/<itemKey>` 和 `siyuan://blocks/<noteDocId>`。
- 前三篇精读分别报告 written、unchanged、preserved、conflict 或 error。
- 返回新增/复用文献数、日报链接、精读写入/保留数及错误。不要清理用户文档或文献，只清理 `WORK`。
