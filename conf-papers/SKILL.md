---
name: conf-papers
description: 使用 Kimi Scholar 检索指定年份和会议的论文，按会议字段过滤、评分并复用 Zotero/思源导入工作流。Use for conference and year paper recommendations.
---

# 顶会论文推荐

## 检索边界

使用 Kimi `scholar.scholar_search`，查询由会议名和不超过 6 个代表性关键词组成，设置年份、每次最多 50 条。读取 `conf-papers.yaml` 获取关键词、排除词、默认会议/年份/top-N；用户参数可覆盖。

本功能不再使用 DBLP，结果是 Scholar 检索集合，不是会议全量列表。必须按返回的 `venue/publication/conference` 字段过滤；字段缺失或会议不符时排除，不根据标题猜测会议。

```bash
python "$SKILL_DIR/scripts/rank_conference_papers.py" \
  --input "$WORK"/*scholar*.csv \
  --config "$SKILL_DIR/conf-papers.yaml" \
  --conferences "ICLR,CVPR" \
  --top-n 10 \
  --output "$WORK/conference.json"
```

评分为相关性 40%、引用热度 40%、摘要质量 20%。读取结果后由 Kimi 撰写概览、摘要、贡献和关键结果。

有 arXiv 版本的前三篇按 `paper-analyze` 阅读全文并生成精读；无全文时只写元数据证据，不伪造分析。需要图片时调用 `extract-paper-images`。

每日式批量推荐可使用 `research_workflow.py` 生成日报和 Note；单篇使用 `--single`。最终说明 Scholar 覆盖边界，并报告 Zotero itemKey、思源链接、写入/保留状态和失败项。
