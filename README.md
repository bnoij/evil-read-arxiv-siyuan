# evil-read-arxiv-siyuan

> 使用 Kimi、思源笔记和 Zotero 的论文搜索、每日推荐、精读与整理工作流

[English](README_en.md) | [快速开始](QUICKSTART.md)

## 工作方式

本项目是一套可在 Kimi Code 和 Kimi Work 中使用的开放 `SKILL.md` 技能集合。

- 论文搜索只使用 Kimi 论文数据库：arXiv 获取近期论文，Scholar 获取热门论文和会议候选。
- Kimi 负责候选去重、评分、摘要、日报、精读、PaperGraph 和冲突处理策略。
- `siyuan-plugin-zotero-notes` 0.2.0 负责 Zotero 写入、思源文档写入和绑定，不生成日报，不擅自覆盖冲突文档。
- 不再提供网页应用，也不依赖其他笔记软件或 Claude/Codex。

## 功能

- `start-my-day`：每日推荐 10 篇，全部进入 Zotero 的 `daily` 分类（不存在时自动创建），生成思源日报，前三篇生成精读。
- `paper-analyze`：分析 arXiv、公开/本地 PDF、研究项目页、博客和普通网页。
- `extract-paper-images`：提取论文图片并上传到思源 `/assets/`。
- `paper-search`：通过思源全文搜索查找已有论文笔记。
- `conf-papers`：使用 Scholar 检索会议论文。结果是 Scholar 子集，不是 DBLP 全量列表。

## 系统要求

- Kimi Code 或 Kimi Work，并启用 arXiv/Scholar 论文数据库。
- Python 3.10+，安装 `requirements.txt` 中依赖。
- 思源 3.7+，桌面端运行。
- Zotero 10+，开启“设置 → 高级 → 允许此计算机上的其他应用与 Zotero 通信”。
- `siyuan-plugin-zotero-notes` 0.2.0，选择目标笔记本并启用“Kimi 研究导入队列”。

## 安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

保留或修改 `config.yaml` 中的研究领域、语言、推荐数量和思源 API 地址。不要在其中写 Token。

### 2. 安装 Zotero 笔记插件

从 [siyuan-plugin-zotero-notes](https://github.com/bnoij/siyuan-plugin-zotero-notes) 获取 0.2.0，将发布包解压到思源工作空间：

```text
data/plugins/siyuan-plugin-zotero-notes/
```

在思源“设置 → 集市 → 已下载”中启用，打开插件设置选择笔记本，保留默认 `Zotero` 根目录或按需修改，并开启导入队列。首次 Zotero 写入时选择 **Always Allow**，供后续定时任务使用。

### 3. 安装 Kimi 技能

Kimi Code 可将五个目录复制到用户或项目的 `.kimi-code/skills/`：

```text
start-my-day/
paper-analyze/
extract-paper-images/
paper-search/
conf-papers/
```

Kimi Work 可在“技能”中安装本地 `.zip` 或 `.md` 技能文件。安装后输入 `/` 调用，或让 Kimi 根据任务自动选择。

### 4. 配置思源 Token

在思源“设置 → 关于”查看 API Token，并配置到当前用户环境变量：

```bash
# macOS/Linux 示例
export SIYUAN_API_TOKEN="<token>"

# Windows PowerShell 当前会话示例
$env:SIYUAN_API_TOKEN="<token>"
```

定时任务应使用持久用户环境变量。Zotero 密钥由插件私有存储管理，不需要写入本项目。

## 文档层级与联动

```text
所选思源笔记本
├── Zotero/
│   └── <论文标题>/
│       └── Note/                  # Kimi 精读和用户后续笔记
└── Research/
    ├── Daily/YYYY-MM-DD 论文推荐/
    └── PaperGraph/
```

论文父文档继续使用插件原有四个属性：

- `custom-zotero-server-id`
- `custom-zotero-item-key`
- `custom-zotero-note-doc-id`
- `custom-zotero-note-key`

因此插件 Dock、元数据刷新、Note 回传和自动回传仍然可用。新增 `custom-research-*` 只用于工作流识别与写入哈希校验。

## 两阶段导入

1. `ensure_papers`：Kimi 提交元数据，插件检查存在性，创建缺失的 Zotero 条目/PDF 链接附件以及论文页/Note，返回 itemKey 和文档 ID。
2. Kimi 生成完整 Markdown，读取当前文档状态并决定写入、跳过、保留或显式覆盖。
3. `write_documents`：插件校验 `expectedHash` 后原样写入。检查到写入之间发生变化时返回 conflict；只有 Kimi 明确 `overwrite` 才覆盖。

已有手工 Note/日报默认保留。重复执行不会重复创建文献或文档。

## 使用

```text
/start-my-day
/paper-analyze 2602.12345
/paper-search "robot learning"
/conf-papers 2026 ICLR,CVPR
```

定时任务提示词见 `schedules/daily-paper-recommendations.md`。在 Kimi Work“定时任务”中设为每天 09:00，并将项目目录指向本仓库。定时运行需要电脑开机，Kimi Work、思源、Zotero 和插件均运行。

## 验证

```bash
python -m unittest discover -s tests -v
python -m compileall -q start-my-day paper-analyze extract-paper-images conf-papers paper-search
```

插件仓库使用 `npm run check` 验证原有 Dock/同步回归与新增导入接口。

## 数据边界

- Zotero 保存元数据和 arXiv PDF 链接附件，不默认存储每天 10 份完整 PDF。
- 精读写入 Note 后，可通过插件回传为 Zotero 子笔记。
- 本版本不迁移旧历史笔记、网页收藏或反馈数据，不批量删除旧数据。
- 搜索、任务文件、PDF 和密钥不得提交到仓库。

## 许可证

MIT，见原项目许可证说明。Zotero 插件仓库使用其自身 AGPL-3.0 许可证。
