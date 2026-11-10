# evil-read-arxiv-siyuan

> Paper discovery, daily recommendations, deep reading, and organization with Kimi, SiYuan, and Zotero

[中文](README.md) | [Quick start](QUICKSTART.md)

## Architecture

This repository provides open `SKILL.md` workflows for Kimi Code and Kimi Work.

- Paper discovery uses only Kimi data sources: arXiv for recent papers and Scholar for influential/conference candidates.
- Kimi owns candidate deduplication, scoring, summaries, reports, analysis, PaperGraph, and conflict policy.
- `siyuan-plugin-zotero-notes` 0.2.0 owns Zotero writes, SiYuan document writes, and bindings. It does not generate reports or overwrite conflicts on its own.
- The former web application and direct paper-search API clients have been removed.

## Skills

- `start-my-day`: recommend 10 papers, import all into Zotero, create a SiYuan report, and deeply analyze the top 3.
- `paper-analyze`: analyze arXiv papers, public/local PDFs, project pages, blogs, and webpages.
- `extract-paper-images`: extract figures and upload them to SiYuan `/assets/`.
- `paper-search`: find existing notes through SiYuan full-text search.
- `conf-papers`: search conference papers with Scholar. Results are a Scholar subset, not a complete DBLP listing.

## Requirements

- Kimi Code or Kimi Work with arXiv/Scholar data sources enabled.
- Python 3.10+ and the dependencies in `requirements.txt`.
- SiYuan 3.7+ desktop and Zotero 10+.
- Zotero local communication enabled under **Settings → Advanced**.
- `siyuan-plugin-zotero-notes` 0.2.0 with a destination notebook and **Kimi research import queue** enabled.

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit research interests, language, recommendation counts, and the SiYuan endpoint in `config.yaml`. Do not store credentials in it.

Install the plugin under `data/plugins/siyuan-plugin-zotero-notes/`, enable it in SiYuan, select a notebook, and enable the import queue. Choose **Always Allow** on the first Zotero write so scheduled jobs can reuse the local authorization.

Install the five skill directories into `.kimi-code/skills` for Kimi Code, or use Kimi Work's local `.zip`/`.md` skill installation. Set the SiYuan API token from **Settings → About** as the persistent `SIYUAN_API_TOKEN` user environment variable. Zotero keys remain in plugin-private storage.

## Document model and bindings

```text
Destination notebook
├── Zotero/
│   └── Paper title/
│       └── Note/                  # Kimi analysis and subsequent user notes
└── Research/
    ├── Daily/YYYY-MM-DD Paper Recommendations/
    └── PaperGraph/
```

The existing `custom-zotero-server-id`, `custom-zotero-item-key`, `custom-zotero-note-doc-id`, and `custom-zotero-note-key` attributes remain the binding source of truth. The Dock, metadata refresh, Note sync, and auto-sync therefore continue to work. `custom-research-*` attributes only identify workflow content and guard write hashes.

## Two-stage import

1. `ensure_papers` checks/creates Zotero items, PDF link attachments, paper documents, Notes, and bindings, returning itemKeys and document IDs.
2. Kimi generates complete Markdown and decides whether to write, skip, preserve, or explicitly overwrite based on current document state.
3. `write_documents` checks `expectedHash` and writes the exact submitted Markdown. A race returns conflict unless Kimi explicitly selects overwrite.

Manual Notes/reports are preserved by default, and retries do not create duplicates.

## Usage and scheduling

```text
/start-my-day
/paper-analyze 2602.12345
/paper-search "robot learning"
/conf-papers 2026 ICLR,CVPR
```

Use `schedules/daily-paper-recommendations.md` to create a persistent 09:00 daily task in Kimi Work. The computer, Kimi Work, SiYuan, Zotero, and the plugin must be running.

## Verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q start-my-day paper-analyze extract-paper-images conf-papers paper-search
```

Run `npm run check` in the plugin repository for Dock/sync regressions and the new import bridge.

## Data boundaries

- Zotero receives metadata and arXiv PDF link attachments, not 10 full PDF files per day by default.
- Analysis in `Note` can be synced back as a Zotero child note through the plugin.
- Historical notes and former web favorites/feedback are not migrated or deleted in bulk.
- Search results, job files, PDFs, and credentials must not be committed.

## License

MIT for this repository. The Zotero plugin retains its AGPL-3.0 license.
