import uuid


def ensure_papers_job(papers):
    return {
        "schemaVersion": 1,
        "id": uuid.uuid4().hex,
        "type": "ensure_papers",
        "payload": {"papers": papers},
    }


def write_documents_job(documents):
    return {
        "schemaVersion": 1,
        "id": uuid.uuid4().hex,
        "type": "write_documents",
        "payload": {"documents": documents},
    }
