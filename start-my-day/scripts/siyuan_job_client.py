#!/usr/bin/env python3
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests

JOB_ROOT = "/data/storage/petal/siyuan-plugin-zotero-notes/jobs"
SUPPORTED_JOBS = {"ensure_papers", "write_documents"}


def canonical_document_markdown(exported) -> str:
    content = exported.get("content", "") if isinstance(exported, dict) else str(exported or "")
    content = re.sub(r"^# [^\n]+(?:\r?\n){2}", "", content, count=1)
    content = re.sub(r'<p class="indent--\d+">([\s\S]*?)</p>', r"\1", content)
    content = re.sub(r"[\u200b-\u200d\ufeff]", "", content)
    return "\n".join("" if not line.strip() else line for line in content.splitlines())


def stable_hash(value) -> str:
    text = str(value or "")
    value = 5381
    data = text.encode("utf-16-le")
    for index in range(0, len(data), 2):
        code_unit = data[index] | (data[index + 1] << 8)
        value = (((value << 5) + value) + code_unit) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = digits[remainder] + result
    return result


class SiYuanJobClient:
    def __init__(self, base_url="http://127.0.0.1:6806", token=None, session=None):
        self.base_url = base_url.rstrip("/")
        self.token = os.environ.get("SIYUAN_API_TOKEN", "") if token is None else token
        self.session = session or requests.Session()

    @property
    def headers(self):
        return {"Authorization": f"Token {self.token}"} if self.token else {}

    def _request(self, path, data=None):
        response = self.session.post(f"{self.base_url}{path}", json=data or {}, headers=self.headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(result.get("msg") or f"SiYuan API failed: {path}")
        return result.get("data")

    def submit_job(self, job):
        job = dict(job)
        job.setdefault("schemaVersion", 1)
        job.setdefault("id", uuid.uuid4().hex)
        if job["type"] not in SUPPORTED_JOBS:
            raise ValueError(f"Unsupported job type: {job['type']}")
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", job["id"]):
            raise ValueError("Invalid job id")
        name = f"{job['id']}.json"
        response = self.session.post(
            f"{self.base_url}/api/file/putFile",
            data={
                "path": f"{JOB_ROOT}/pending/{name}",
                "isDir": "false",
                "modTime": str(int(time.time())),
            },
            files={"file": (name, json.dumps(job, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")},
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(result.get("msg") or "Unable to submit job")
        return job["id"]

    def _read_job(self, job_id):
        for directory in ("completed", "failed"):
            response = self.session.post(
                f"{self.base_url}/api/file/getFile",
                json={"path": f"{JOB_ROOT}/{directory}/{job_id}.json"},
                headers={**self.headers, "Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code in (202, 404):
                continue
            response.raise_for_status()
            try:
                result = response.json()
            except ValueError:
                continue
            if isinstance(result, dict) and result.get("code") not in (None, 0):
                continue
            if isinstance(result, dict) and result.get("id") == job_id:
                return result
        return None

    def wait_for_job(self, job_id, timeout=900, poll_interval=2):
        deadline = time.monotonic() + timeout
        while True:
            result = self._read_job(job_id)
            if result is not None:
                return result
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Workflow job {job_id} did not finish within {timeout} seconds")
            time.sleep(poll_interval)

    def get_document_state(self, doc_id="", path=""):
        if not doc_id and path:
            escaped = path.replace("'", "''")
            rows = self._request("/api/query/sql", {"stmt": f"SELECT id FROM blocks WHERE type = 'doc' AND hpath = '{escaped}' LIMIT 1"})
            doc_id = rows[0]["id"] if rows else ""
        if not doc_id:
            return {"exists": False, "docId": "", "path": path, "contentHash": stable_hash(""), "attrs": {}}
        exported = self._request("/api/lute/copyStdMarkdown", {"id": doc_id})
        attrs = self._request("/api/attr/getBlockAttrs", {"id": doc_id}) or {}
        return {
            "exists": True,
            "docId": doc_id,
            "path": path,
            "contentHash": stable_hash(canonical_document_markdown(exported)),
            "attrs": attrs,
        }

    def search_notes(self, query, limit=20):
        data = self._request("/api/search/fullTextSearchBlock", {
            "query": query,
            "page": 1,
            "paths": [],
            "boxes": [],
            "types": {"document": True, "heading": True, "paragraph": True},
            "method": 0,
            "orderBy": 0,
            "groupBy": 0,
        }) or {}
        results = []
        for block in (data.get("blocks") or [])[:limit]:
            block_id = block.get("id") or block.get("block_id") or block.get("root_id")
            if not block_id:
                continue
            results.append({
                "id": block_id,
                "title": block.get("content") or block.get("hPath") or block_id,
                "path": block.get("hPath") or "",
                "url": f"siyuan://blocks/{block_id}",
            })
        return results

    def upload_assets(self, paths, assets_dir="/assets/"):
        uploaded = []
        for source in paths:
            path = Path(source)
            with path.open("rb") as handle:
                response = self.session.post(
                    f"{self.base_url}/api/asset/upload",
                    data={"assetsDirPath": assets_dir},
                    files={"file[]": (path.name, handle, "application/octet-stream")},
                    headers=self.headers,
                    timeout=120,
                )
            response.raise_for_status()
            result = response.json()
            if result.get("code") != 0:
                raise RuntimeError(result.get("msg") or f"Unable to upload {path.name}")
            data = result.get("data") or {}
            if data.get("errFiles"):
                raise RuntimeError(f"Unable to upload {path.name}: {data['errFiles']}")
            uploaded.extend((data.get("succMap") or {}).values())
        return uploaded
