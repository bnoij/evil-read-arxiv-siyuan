# Kimi Work 定时任务：每日论文推荐

- 时间：每天 09:00（本地时区）
- 项目目录：本仓库根目录
- 调用技能：`start-my-day`

## 任务提示词

调用 `start-my-day`，使用当前日期和仓库根目录的 `config.yaml` 执行每日论文推荐。必须使用 Kimi arXiv/Scholar 数据源，并确保 siyuan-plugin-zotero-notes 0.2.0 的导入队列已启用。

完成后汇报：

1. Zotero 新增、复用和失败的文献数量。
2. 思源日报的路径与可点击链接。
3. 前三篇精读的 written、unchanged、preserved、conflict、error 数量。
4. 任一 partial/failed 的具体原因；不得把部分成功汇报为全部成功。

若 Kimi Work、思源、Zotero、插件或本机 API 不可用，停止并报告阻塞原因，不生成空日报，不使用旧论文搜索脚本。
