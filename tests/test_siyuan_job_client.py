import importlib.util
import json
import time
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jobs = load_module("siyuan_job_client", "start-my-day/scripts/siyuan_job_client.py")


class SiYuanJobClientTests(unittest.TestCase):
    def test_submit_job_writes_pending_json_with_token(self):
        session = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 0, "msg": "", "data": None}
        session.post.return_value = response
        client = jobs.SiYuanJobClient("http://127.0.0.1:6806", "secret-token", session=session)

        job_id = client.submit_job({"id": "job-1", "type": "ensure_papers", "payload": {"papers": []}})

        self.assertEqual(job_id, "job-1")
        _, kwargs = session.post.call_args
        self.assertEqual(kwargs["data"]["path"], "/data/storage/petal/siyuan-plugin-zotero-notes/jobs/pending/job-1.json")
        self.assertEqual(kwargs["headers"]["Authorization"], "Token secret-token")
        sent = json.loads(kwargs["files"]["file"][1].decode("utf-8"))
        self.assertEqual(sent["type"], "ensure_papers")

    def test_wait_for_job_returns_partial_and_failed_results(self):
        client = jobs.SiYuanJobClient()
        client._read_job = Mock(side_effect=[
            {"id": "a", "status": "partial", "result": {"papers": []}},
            {"id": "b", "status": "failed", "error": "denied"},
        ])

        partial = client.wait_for_job("a", timeout=1, poll_interval=0)
        failed = client.wait_for_job("b", timeout=1, poll_interval=0)

        self.assertEqual(partial["status"], "partial")
        self.assertEqual(failed["error"], "denied")

    def test_wait_for_job_timeout_does_not_submit_another_job(self):
        client = jobs.SiYuanJobClient()
        client._read_job = Mock(return_value=None)
        client.submit_job = Mock()
        started = time.monotonic()

        with self.assertRaises(TimeoutError):
            client.wait_for_job("slow", timeout=0.01, poll_interval=0)

        client.submit_job.assert_not_called()
        self.assertLess(time.monotonic() - started, 1)

    def test_document_state_by_path_uses_siyuan_document_type_code(self):
        client = jobs.SiYuanJobClient()
        client._request = Mock(side_effect=[[{"id": "doc-path"}], {"content": "body"}, {}])

        state = client.get_document_state(path="/Research/PaperGraph")

        self.assertTrue(state["exists"])
        statement = client._request.call_args_list[0][0][1]["stmt"]
        self.assertIn("type = 'd'", statement)

    def test_document_state_uses_normalized_content_hash(self):
        client = jobs.SiYuanJobClient()
        client._request = Mock(side_effect=[
            {"hPath": "/Note", "content": "body"},
            {"custom-research-workflow": "evil-read-arxiv"},
        ])

        state = client.get_document_state(doc_id="doc-1")

        self.assertTrue(state["exists"])
        self.assertEqual(state["contentHash"], jobs.stable_hash("body"))
        self.assertEqual(state["attrs"]["custom-research-workflow"], "evil-read-arxiv")

    def test_empty_note_placeholder_hash_matches_plugin(self):
        exported = "# Note\n\n　　‍\n"
        client = jobs.SiYuanJobClient()
        client._request = Mock(side_effect=[exported, {}])

        state = client.get_document_state(doc_id="doc-empty")

        self.assertEqual(jobs.stable_hash(jobs.canonical_document_markdown(exported)), jobs.stable_hash("\n"))
        self.assertEqual(state["contentHash"], jobs.stable_hash("\n"))
        self.assertTrue(state["empty"])

    def test_search_notes_returns_siyuan_links(self):
        client = jobs.SiYuanJobClient()
        client._request = Mock(return_value={"blocks": [{"id": "doc1", "content": "Paper title", "hPath": "/Zotero/Paper"}]})

        results = client.search_notes("Paper")

        self.assertEqual(results[0]["url"], "siyuan://blocks/doc1")
        self.assertEqual(results[0]["title"], "Paper title")

    def test_upload_assets_returns_siyuan_paths(self):
        session = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": "",
            "data": {"errFiles": [], "succMap": {"figure.png": "assets/figure-id.png"}},
        }
        session.post.return_value = response
        client = jobs.SiYuanJobClient(session=session)
        source = Path(__file__)

        self.assertEqual(client.upload_assets([source]), ["assets/figure-id.png"])


if __name__ == "__main__":
    unittest.main()
