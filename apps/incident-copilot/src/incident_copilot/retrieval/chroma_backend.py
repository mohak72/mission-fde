"""The only module in this project permitted to import chromadb.

[Source: architecture/coding-standards.md#critical-rules]

Uses the embedded `PersistentClient` (in-process, no network listener) rather
than Chroma's HTTP server -- see Story 1.3 Completion Notes for why: the
server has open CVEs with no fix version available as of 2026-11-06.
"""

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from incident_copilot.config import settings

EMBEDDING_MODEL_NAME = ONNXMiniLM_L6_V2.MODEL_NAME

_client: chromadb.ClientAPI | None = None
_embedding_function = ONNXMiniLM_L6_V2()


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    return _client


def reset_client() -> None:
    """Forces the next call to rebuild the client from current settings.

    Exists for integration tests that need a dedicated, uniquely-named
    collection/persist directory per session (Test Strategy's test-data
    isolation rule) -- without this, the client would be frozen at whatever
    path was live the first time this module was imported.
    """
    global _client
    _client = None


def _get_collection() -> Collection:
    return _get_client().get_or_create_collection(
        name=settings.chroma_collection_name,
        embedding_function=_embedding_function,
    )


def upsert_embedding(runbook_id: str, content: str) -> None:
    """Embeds `content` and upserts it, keyed by `runbook_id`.

    Chroma computes the embedding internally via the collection's attached
    embedding function -- callers never handle a raw vector.
    """
    _get_collection().upsert(ids=[runbook_id], documents=[content])


def query_nearest(query_text: str, n_results: int = 1) -> list[str]:
    """Returns the nearest runbook ids for `query_text`, most similar first.

    Embedded with the same collection-attached embedding function used at
    index time -- this is what keeps query and index vectors comparable.
    """
    result = _get_collection().query(query_texts=[query_text], n_results=n_results)
    ids = result["ids"][0]
    return list(ids)
