# 快速开始

## 1. 准备应用

1. 安装 Kimi Code 或 Kimi Work，并启用 arXiv/Scholar 论文数据库。
2. 启动思源 3.7+，在“设置 → 关于”找到 API Token。
3. 启动 Zotero 10+，在“设置 → 高级”允许其他应用通信。
4. 安装并启用 `siyuan-plugin-zotero-notes` 0.2.0，选择目标笔记本并开启“Kimi 研究导入队列”。

## 2. 配置项目

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

编辑 `config.yaml` 的研究领域、语言和推荐数量。配置持久环境变量 `SIYUAN_API_TOKEN`，不要把 Token 写进 YAML 或源码。

第一次导入时，在 Zotero 授权弹窗选择 **Always Allow**。之后 Zotero 密钥由插件管理。

## 3. 安装技能

将以下目录复制到 `.kimi-code/skills/`，或在 Kimi Work 技能页安装本地技能包：

```text
start-my-day
paper-analyze
extract-paper-images
paper-search
conf-papers
```

保持这些目录与仓库脚本、配置的相对位置。Kimi Work 定时任务应把项目目录挂载为仓库根目录。

## 4. 验证每日推荐

在 Kimi 中运行：

```text
/start-my-day
```

预期结果：

- 10 篇推荐均能在 Zotero 查到，并带 arXiv PDF 链接附件。
- 思源生成 `Research/Daily/<日期> 论文推荐`。
- 每篇有 `Zotero/<论文>/Note`，前三篇包含精读和有效 assets 图片。
- 日报同时包含 Zotero 和 `siyuan://blocks/` 链接。
- 再执行一次不会重复创建，也不会覆盖手工 Note。

可在 Zotero 插件 Dock 中打开 Note、刷新元数据或回传 Note。刷新元数据不会改写 Note。

## 5. 创建定时任务

在 Kimi Work“定时任务”中新建每天 09:00 的任务，项目目录选择本仓库，提示词使用 `schedules/daily-paper-recommendations.md`。

电脑、Kimi Work、思源、Zotero 和插件必须运行。若任务失败，先检查 Token、插件队列和 Zotero 授权，不要改用旧搜索脚本。

## 测试

```bash
python -m unittest discover -s tests -v
```

全部测试通过后，再手动触发一次定时任务，核对新增/复用文献数、日报链接和精读写入/保留状态。
