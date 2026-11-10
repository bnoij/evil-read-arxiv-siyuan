import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = load_module("research_workflow", "start-my-day/scripts/research_workflow.py")
jobs = load_module("siyuan_job_client_for_workflow", "start-my-day/scripts/siyuan_job_client.py")


def paper(**changes):
    value = {
        "arxiv_id": "2601.00001",
        "title": "A Research Paper",
        "authors": ["Author One"],
        "published": "2026-01-02",
        "url": "https://arxiv.org/abs/2601.00001",
        "pdf_url": "https://arxiv.org/pdf/2601.00001",
        "summary": "One sentence",
        "contributions": ["Contribution"],
        "key_results": "Result",
        "analysis_markdown": "## Analysis",
        "itemKey": "ITEM1",
        "noteDocId": "NOTE1",
        "parentDocId": "PARENT1",
    }
    value.update(changes)
    return value


class ResearchWorkflowTests(unittest.TestCase):
    def test_daily_markdown_contains_both_links_and_kimi_content(self):
        markdown = workflow.render_daily_markdown(
            "2026-11-10",
            "Today's overview",
            [paper()],
            language="en",
        )

        self.assertIn("Today's overview", markdown)
        self.assertIn("zotero://select/library/items/ITEM1", markdown)
        self.assertIn("siyuan://blocks/NOTE1", markdown)
        self.assertIn("Contribution", markdown)

    def test_json_stdout_is_always_utf8(self):
        buffer = io.BytesIO()
        stdout = type("Stdout", (), {"buffer": buffer})()

        with patch.object(sys, "stdout", stdout):
            workflow.emit_json({"title": "论文推荐"})

        self.assertIn("论文推荐", buffer.getvalue().decode("utf-8"))

    def test_empty_note_is_written_with_current_hash(self):
        state = {"exists": True, "contentHash": jobs.stable_hash(""), "attrs": {}}

        documents, decisions = workflow.prepare_write_documents(
            [paper()],
            "/Research/Daily/2026-11-10",
            "/Research/PaperGraph",
            "daily",
            "graph",
            lambda **_kwargs: state,
        )

        note = next(item for item in documents if item.get("docId") == "NOTE1")
        self.assertEqual(note["markdown"], "## Analysis")
        self.assertEqual(note["expectedHash"], jobs.stable_hash(""))
        self.assertEqual(note["onConflict"], "report")
        self.assertEqual(decisions["NOTE1"]["status"], "write")

    def test_placeholder_empty_note_remains_writable_after_hash_alignment(self):
        state = {"exists": True, "empty": True, "contentHash": jobs.stable_hash("\n"), "attrs": {}}

        documents, _ = workflow.prepare_write_documents(
            [paper()], "/daily", "/graph", "daily", "graph", lambda **_kwargs: state
        )

        self.assertEqual(next(item for item in documents if item.get("docId") == "NOTE1")["expectedHash"], jobs.stable_hash("\n"))

    def test_manual_note_is_preserved_without_a_write_operation(self):
        state = {"exists": True, "contentHash": jobs.stable_hash("manual"), "attrs": {}}

        documents, decisions = workflow.prepare_write_documents(
            [paper()],
            "/Research/Daily/2026-11-10",
            "/Research/PaperGraph",
            "daily",
            "graph",
            lambda **_kwargs: state,
        )

        self.assertFalse(any(item.get("docId") == "NOTE1" for item in documents))
        self.assertEqual(decisions["NOTE1"]["status"], "preserved")

    def test_unchanged_ai_note_is_skipped_and_force_allows_overwrite(self):
        current_hash = jobs.stable_hash("## Analysis")
        state = {
            "exists": True,
            "contentHash": current_hash,
            "attrs": {
                "custom-research-workflow": "evil-read-arxiv",
                "custom-research-content-hash": current_hash,
            },
        }

        documents, decisions = workflow.prepare_write_documents(
            [paper()], "/daily", "/graph", "daily", "graph", lambda **_kwargs: state
        )
        forced, _ = workflow.prepare_write_documents(
            [paper()], "/daily", "/graph", "daily", "graph", lambda **_kwargs: state, force=True
        )

        self.assertFalse(any(item.get("docId") == "NOTE1" for item in documents))
        self.assertEqual(decisions["NOTE1"]["status"], "unchanged")
        self.assertEqual(next(item for item in forced if item.get("docId") == "NOTE1")["onConflict"], "overwrite")

    def test_exported_indentation_still_counts_as_unchanged_ai_content(self):
        markdown = paper()["analysis_markdown"]
        exported = markdown.replace("本文", "　　本文") if "本文" in markdown else "　　" + markdown
        current_hash = jobs.stable_hash(jobs.canonical_document_markdown(exported))
        state = {
            "exists": True,
            "contentHash": current_hash,
            "contentFingerprint": jobs.content_fingerprint(exported),
            "attrs": {
                "custom-research-workflow": "evil-read-arxiv",
                "custom-research-content-hash": current_hash,
            },
        }

        documents, decisions = workflow.prepare_write_documents(
            [paper()], "/daily", "/graph", "daily", "graph", lambda **_kwargs: state
        )

        self.assertFalse(any(item.get("docId") == "NOTE1" for item in documents))
        self.assertEqual(decisions["NOTE1"]["status"], "unchanged")

    def test_daily_workflow_submits_ensure_then_exact_markdown_writes(self):
        class FakeClient:
            def __init__(self):
                self.jobs = []

            def submit_job(self, job):
                self.jobs.append(job)
                return job["id"]

            def wait_for_job(self, job_id, **_kwargs):
                if job_id == "ensure":
                    return {"status": "completed", "result": {"papers": [{
                        "arxivId": "2601.00001",
                        "itemKey": "ITEM1",
                        "parentDocId": "PARENT1",
                        "noteDocId": "NOTE1",
                        "itemStatus": "created",
                    }]}}
                return {"status": "completed", "result": {"documents": []}}

            def get_document_state(self, **_kwargs):
                return {"exists": False, "contentHash": jobs.stable_hash(""), "attrs": {}}

        client = FakeClient()
        ranked = {"top_papers": [paper(itemKey="", noteDocId="", parentDocId="")]}
        original_submit = client.submit_job

        def assign_ids(job):
            if job["type"] == "ensure_papers":
                job["id"] = "ensure"
            elif job["type"] == "write_documents":
                job["id"] = "write"
            return original_submit(job)

        client.submit_job = assign_ids

        result = workflow.run_daily_workflow(
            client,
            {"siyuan": {"daily_root": "/Research/Daily", "graph_path": "/Research/PaperGraph"}},
            ranked,
            "Overview",
            target_date="2026-11-10",
        )

        self.assertEqual([job["type"] for job in client.jobs], ["ensure_papers", "write_documents"])
        writes = client.jobs[1]["payload"]["documents"]
        daily = next(item for item in writes if item.get("path") == "/Research/Daily/2026-11-10 论文推荐")
        self.assertIn("zotero://select/library/items/ITEM1", daily["markdown"])
        self.assertEqual(result["dailyDocPath"], daily["path"])

    def test_single_paper_analysis_does_not_create_a_daily_document(self):
        class FakeClient:
            def __init__(self):
                self.jobs = []

            def submit_job(self, job):
                self.jobs.append(job)
                return "ensure" if job["type"] == "ensure_papers" else "write"

            def wait_for_job(self, job_id, **_kwargs):
                if job_id == "ensure":
                    return {"status": "completed", "result": {"papers": [{
                        "arxivId": "2601.00001", "itemKey": "ITEM1", "parentDocId": "PARENT1", "noteDocId": "NOTE1", "itemStatus": "created"
                    }]}}
                return {"status": "completed", "result": {"documents": []}}

            def get_document_state(self, **_kwargs):
                return {"exists": False, "contentHash": jobs.stable_hash(""), "attrs": {}}

        client = FakeClient()
        result = workflow.run_paper_analysis(
            client,
            {"siyuan": {"graph_path": "/Research/PaperGraph"}},
            paper(itemKey="", noteDocId="", parentDocId=""),
        )

        self.assertEqual([job["type"] for job in client.jobs], ["ensure_papers", "write_documents"])
        writes = client.jobs[1]["payload"]["documents"]
        self.assertFalse(any(item.get("path", "").startswith("/Research/Daily") for item in writes))
        self.assertEqual(result["noteDocId"], "NOTE1")


if __name__ == "__main__":
    unittest.main()
