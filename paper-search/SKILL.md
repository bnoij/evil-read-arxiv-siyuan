---
name: paper-search
description: 在思源已有论文笔记中按标题、作者、关键词、领域或 arXiv ID 搜索并返回思源链接。Use when revisiting existing notes rather than finding new papers.
---

# 搜索已有论文笔记

使用 `start-my-day/scripts/siyuan_job_client.py` 中的 `SiYuanJobClient.search_notes(query)`，它通过思源全文搜索接口读取已有内容。不要扫描本地 Markdown，也不要用本技能搜索新论文。

执行方式示例：

```bash
python -c "import sys; sys.path.insert(0, '$SKILL_DIR/../start-my-day/scripts'); from siyuan_job_client import SiYuanJobClient; import json; print(json.dumps(SiYuanJobClient().search_notes('<query>'), ensure_ascii=False, indent=2))"
```

按标题、作者、关键词或 arXiv ID 构造查询。结果包含标题、路径和 `siyuan://blocks/<id>`。按标题匹配、作者匹配、正文匹配排序，去重后展示；空结果时建议更短关键词或相关领域词。环境需要 `SIYUAN_API_TOKEN`，失败时报告 API 错误，不伪造结果。
