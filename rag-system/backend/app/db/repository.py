"""
Metadata database repository.

The spec recommends MongoDB. This prototype ships a sqlite3-backed
implementation of the same Repository interface (zero external services to
install/run, works anywhere) with collections matching the spec 1:1:

    sources, documents, document_versions, knowledge_items, chunks,
    processing_jobs, provenance_records, retrieval_logs

To move to MongoDB in production: implement `MongoRepository` against this
same interface (using pymongo, `mongodb_uri` / `mongodb_db_name` from
app.core.config.settings) and select it via DB_BACKEND=mongodb. No other
module imports sqlite3 directly -- everything goes through `Repository`.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from app.core.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    source_id TEXT,
    url TEXT,
    content_hash TEXT,
    version INTEGER,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE TABLE IF NOT EXISTS document_versions (
    document_id TEXT,
    version INTEGER,
    data TEXT NOT NULL,
    PRIMARY KEY (document_id, version)
);
CREATE TABLE IF NOT EXISTS knowledge_items (
    knowledge_id TEXT PRIMARY KEY,
    document_id TEXT,
    knowledge_type TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    knowledge_type TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS provenance_records (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS retrieval_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return obj


class SQLiteRepository:
    def __init__(self, path: str = None):
        self.path = path or settings.sqlite_path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=30.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- generic upsert helper ---
    def _upsert(self, table: str, key_col: str, key_val: str, extra_cols: Dict[str, Any], obj: Any):
        payload = json.dumps(_to_jsonable(obj))
        cols = [key_col] + list(extra_cols.keys()) + ["data"]
        placeholders = ",".join(["?"] * len(cols))
        values = [key_val] + list(extra_cols.values()) + [payload]
        with self._conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                values,
            )

    def _get(self, table: str, key_col: str, key_val: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(f"SELECT data FROM {table} WHERE {key_col} = ?", (key_val,)).fetchone()
        return json.loads(row[0]) if row else None

    def _list(self, table: str, where: str = "", params: tuple = ()) -> List[dict]:
        query = f"SELECT data FROM {table}"
        if where:
            query += f" WHERE {where}"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [json.loads(r[0]) for r in rows]

    # --- sources ---
    def upsert_source(self, source):
        self._upsert("sources", "source_id", source.source_id, {}, source)

    def get_source(self, source_id: str) -> Optional[dict]:
        return self._get("sources", "source_id", source_id)

    def list_sources(self) -> List[dict]:
        return self._list("sources")

    # --- documents ---
    def upsert_document(self, document):
        self._upsert(
            "documents", "document_id", document.document_id,
            {"source_id": document.source_id, "url": document.url,
             "content_hash": document.content_hash, "version": document.version},
            document,
        )

    def get_document(self, document_id: str) -> Optional[dict]:
        return self._get("documents", "document_id", document_id)

    def find_document_by_url(self, url: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM documents WHERE url = ?", (url,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_documents(self, source_id: Optional[str] = None) -> List[dict]:
        if source_id:
            return self._list("documents", "source_id = ?", (source_id,))
        return self._list("documents")

    def delete_document(self, document_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM document_versions WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM knowledge_items WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM provenance_records WHERE document_id = ?", (document_id,))
        return True

    # --- document_versions ---
    def add_document_version(self, doc_version):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO document_versions (document_id, version, data) VALUES (?,?,?)",
                (doc_version.document_id, doc_version.version, json.dumps(_to_jsonable(doc_version))),
            )

    def list_document_versions(self, document_id: str) -> List[dict]:
        return self._list("document_versions", "document_id = ?", (document_id,))

    # --- knowledge_items ---
    def upsert_knowledge_item(self, item):
        self._upsert(
            "knowledge_items", "knowledge_id", item.knowledge_id,
            {"document_id": item.document_id, "knowledge_type": item.knowledge_type.value
             if hasattr(item.knowledge_type, "value") else item.knowledge_type},
            item,
        )

    def get_knowledge_item(self, knowledge_id: str) -> Optional[dict]:
        return self._get("knowledge_items", "knowledge_id", knowledge_id)

    def list_knowledge_items(self, knowledge_type: Optional[str] = None) -> List[dict]:
        if knowledge_type:
            return self._list("knowledge_items", "knowledge_type = ?", (knowledge_type,))
        return self._list("knowledge_items")

    def delete_knowledge_items_for_document(self, document_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM knowledge_items WHERE document_id = ?", (document_id,))

    # --- chunks ---
    def upsert_chunks(self, chunks: List[Any]):
        with self._conn() as conn:
            for c in chunks:
                kt = c.knowledge_type.value if hasattr(c.knowledge_type, "value") else c.knowledge_type
                conn.execute(
                    "INSERT OR REPLACE INTO chunks (chunk_id, document_id, knowledge_type, data) VALUES (?,?,?,?)",
                    (c.chunk_id, c.document_id, kt, json.dumps(_to_jsonable(c))),
                )

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        return self._get("chunks", "chunk_id", chunk_id)

    def list_chunks_for_document(self, document_id: str) -> List[dict]:
        return self._list("chunks", "document_id = ?", (document_id,))

    def delete_chunks_for_document(self, document_id: str) -> List[str]:
        chunks = self.list_chunks_for_document(document_id)
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM provenance_records WHERE document_id = ?", (document_id,))
        return [c["chunk_id"] for c in chunks]

    # --- processing_jobs ---
    def upsert_job(self, job):
        self._upsert("processing_jobs", "job_id", job.job_id, {}, job)

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._get("processing_jobs", "job_id", job_id)

    def list_jobs(self) -> List[dict]:
        return self._list("processing_jobs")

    # --- provenance_records ---
    def upsert_provenance(self, record):
        self._upsert(
            "provenance_records", "chunk_id", record.chunk_id,
            {"document_id": record.document_id}, record,
        )

    def list_provenance_for_document(self, document_id: str) -> List[dict]:
        return self._list("provenance_records", "document_id = ?", (document_id,))

    # --- retrieval_logs ---
    def add_retrieval_log(self, log: dict):
        try:
            with self._conn() as conn:
                conn.execute("INSERT INTO retrieval_logs (data) VALUES (?)", (json.dumps(_to_jsonable(log)),))
        except Exception as e:
            logger.debug("Non-fatal retrieval audit log error: %s", e)

    # --- system_state ---
    def set_system_state(self, key: str, value: Any):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)",
                (key, json.dumps(_to_jsonable(value))),
            )

    def get_system_state(self, key: str, default: Any = None) -> Any:
        try:
            with self._conn() as conn:
                cur = conn.execute("SELECT value FROM system_state WHERE key = ?", (key,))
                row = cur.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            pass
        return default


_repository_singleton: Optional[SQLiteRepository] = None


def get_repository() -> SQLiteRepository:
    global _repository_singleton
    if _repository_singleton is None:
        _repository_singleton = SQLiteRepository()
    return _repository_singleton
