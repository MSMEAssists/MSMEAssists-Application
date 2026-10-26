"""
Automated Periodic Background Scheduler Service.

Runs periodic knowledge base ingestion & schema updates automatically
every 24 hours (or configured interval) in a non-blocking background task.
"""
import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.source_registry import ApprovedSource, DEFAULT_APPROVED_SOURCES
from app.db.repository import SQLiteRepository, get_repository
from app.embeddings.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.vectorstore.factory import build_vector_store

logger = logging.getLogger(__name__)


class AutoIngestionScheduler:
    def __init__(self, repository: Optional[SQLiteRepository] = None):
        self.repository = repository
        self.enabled: bool = settings.auto_ingestion_enabled
        self.interval_hours: int = settings.auto_ingestion_interval_hours
        self.max_pages: int = settings.auto_ingestion_max_pages
        self.run_on_startup: bool = settings.auto_ingestion_run_on_startup
        self.startup_grace_seconds: float = float(settings.auto_ingestion_startup_grace_seconds)

        self.is_running: bool = False
        self.is_active: bool = False
        self._task: Optional[asyncio.Task] = None
        self._run_lock: threading.Lock = threading.Lock()
        self._start_lock: Optional[asyncio.Lock] = None

        self.last_run_at: Optional[float] = None
        self.next_run_at: Optional[float] = None
        self.last_job_id: Optional[str] = None
        self.last_job_summary: Optional[Dict[str, Any]] = None

        # Load persisted state from repository and compute next_run_at
        self.load_state()

    def _get_repo(self) -> SQLiteRepository:
        if self.repository is not None:
            return self.repository
        return get_repository()

    def _get_approved_sources(self, repo: SQLiteRepository) -> List[ApprovedSource]:
        stored = {s["source_id"]: s for s in repo.list_sources()} if hasattr(repo, "list_sources") else {}
        if not stored:
            return list(DEFAULT_APPROVED_SOURCES)
        sources: List[ApprovedSource] = []
        for default in DEFAULT_APPROVED_SOURCES:
            row = stored.get(default.source_id)
            if row:
                sources.append(ApprovedSource(**{**default.__dict__, **{k: v for k, v in row.items() if k in default.__dict__}}))
            else:
                sources.append(default)
        for source_id, row in stored.items():
            if source_id not in {d.source_id for d in DEFAULT_APPROVED_SOURCES}:
                try:
                    sources.append(ApprovedSource(**row))
                except Exception:
                    pass
        return sources

    def load_state(self):
        """Restore scheduler state from the database and recalculate next_run_at."""
        try:
            repo = self._get_repo()
            if repo and hasattr(repo, "get_system_state"):
                state = repo.get_system_state("scheduler_state", default={})
                if state and isinstance(state, dict):
                    self.last_run_at = state.get("last_run_at", self.last_run_at)
                    self.last_job_id = state.get("last_job_id", self.last_job_id)
                    self.last_job_summary = state.get("last_job_summary", self.last_job_summary)
                    if "interval_hours" in state:
                        self.interval_hours = int(state["interval_hours"])
                    if "enabled" in state:
                        self.enabled = bool(state["enabled"])
                    if "run_on_startup" in state:
                        self.run_on_startup = bool(state["run_on_startup"])
        except Exception as e:
            logger.debug("Failed to load scheduler state from DB: %s", e)

        self.next_run_at = self.recalculate_next_run()

    def persist_state(self):
        """Save current scheduler state to repository."""
        try:
            repo = self._get_repo()
            if repo and hasattr(repo, "set_system_state"):
                state = {
                    "last_run_at": self.last_run_at,
                    "next_run_at": self.next_run_at,
                    "last_job_id": self.last_job_id,
                    "last_job_summary": self.last_job_summary,
                    "interval_hours": self.interval_hours,
                    "enabled": self.enabled,
                    "run_on_startup": self.run_on_startup,
                }
                repo.set_system_state("scheduler_state", state)
        except Exception as e:
            logger.warning("Failed to persist scheduler state: %s", e)

    def recalculate_next_run(self, now: Optional[float] = None) -> float:
        """Compute the next scheduled run timestamp based on interval, last_run_at, and startup rules."""
        now = now if now is not None else time.time()
        interval_seconds = self.interval_hours * 3600

        if self.last_run_at is not None:
            next_due = self.last_run_at + interval_seconds
            if next_due > now:
                return next_due
            else:
                # Missed/overdue run while application was stopped
                if self.run_on_startup:
                    return now + self.startup_grace_seconds
                else:
                    return now + interval_seconds
        else:
            # Fresh database / first-time deployment
            if self.run_on_startup:
                return now + self.startup_grace_seconds
            else:
                return now + interval_seconds

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_hours": self.interval_hours,
            "run_on_startup": self.run_on_startup,
            "is_active": self.is_active,
            "is_currently_running_job": self.is_running,
            "last_run_at": datetime.fromtimestamp(self.last_run_at, timezone.utc).isoformat() if self.last_run_at else None,
            "next_run_at": datetime.fromtimestamp(self.next_run_at, timezone.utc).isoformat() if self.next_run_at else None,
            "last_job_id": self.last_job_id,
            "last_job_summary": self.last_job_summary,
        }

    def configure(
        self,
        enabled: Optional[bool] = None,
        interval_hours: Optional[int] = None,
        run_on_startup: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Dynamically reconfigure scheduler parameters and recalculate next_run_at."""
        recalc = False
        if enabled is not None:
            self.enabled = enabled
        if interval_hours is not None and interval_hours > 0:
            self.interval_hours = interval_hours
            recalc = True
        if run_on_startup is not None:
            self.run_on_startup = run_on_startup
            recalc = True

        if recalc:
            self.next_run_at = self.recalculate_next_run()

        self.persist_state()
        return self.get_status()

    async def start(self):
        if self._start_lock is None:
            self._start_lock = asyncio.Lock()
        async with self._start_lock:
            if self.is_active and self._task and not self._task.done():
                logger.info("AutoIngestionScheduler already active.")
                return

            self.is_active = True
            if self.next_run_at is None:
                self.next_run_at = self.recalculate_next_run()
                self.persist_state()
            self._task = asyncio.create_task(self._scheduler_loop())
            next_iso = datetime.fromtimestamp(self.next_run_at, timezone.utc).isoformat() if self.next_run_at else "N/A"
            logger.info("AutoIngestionScheduler started. Configured interval: %d hours. Next run at: %s", self.interval_hours, next_iso)

    async def stop(self):
        self.is_active = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("AutoIngestionScheduler stopped.")

    async def run_now(self) -> Dict[str, Any]:
        """Manually trigger an immediate background update run, preventing overlaps."""
        from app.services.ingestion_service import is_ingestion_running
        if self.is_running or is_ingestion_running():
            return {"status": "error", "message": "An ingestion job is already running."}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._execute_ingestion)

    def _execute_ingestion(self) -> Dict[str, Any]:
        """Execute one complete cycle of government discovery and ingestion.
        Guarantees non-overlapping execution and handles individual failures without crashing."""
        from app.services.ingestion_service import is_ingestion_running

        acquired = self._run_lock.acquire(blocking=False)
        if not acquired or is_ingestion_running():
            logger.warning("Ingestion run already in progress. Rejecting overlapping run.")
            return {"status": "error", "message": "An ingestion job is already running."}

        self.is_running = True
        self.last_run_at = time.time()
        logger.info("Starting automated periodic knowledge base ingestion run...")

        summary: Dict[str, Any] = {
            "status": "error",
            "discovery_discovered": 0,
            "discovery_ingested": 0,
            "web_discovered": 0,
            "web_ingested": 0,
            "web_unchanged": 0,
            "local_ingested": 0,
            "local_unchanged": 0,
            "errors": [],
        }

        try:
            repo = self._get_repo()

            # Prevent overlap with external running jobs in the repository
            stale_threshold = time.time() - 7200
            running_jobs = [
                j for j in repo.list_jobs()
                if isinstance(j, dict) and j.get("status") == "running" and j.get("started_at", 0) > stale_threshold
            ]
            if running_jobs:
                logger.warning("Another ingestion job is already marked as running in repository.")
                summary["status"] = "error"
                summary["message"] = "Another ingestion job is already running."
                summary["skipped_due_to_overlap"] = True
                self.last_job_summary = summary
                self.next_run_at = time.time() + 300  # retry in 5 minutes rather than skipping full day
                self.persist_state()
                return summary

            vs = build_vector_store()
            es = EmbeddingService()
            approved_sources = self._get_approved_sources(repo)
            svc = IngestionService(
                repository=repo,
                vector_store=vs,
                embedding_service=es,
                approved_sources=approved_sources,
            )

            # Phase 1: Government Source Discovery (Sitemaps, robots.txt, scheme dirs)
            # Register newly discovered portals without duplicate crawling/ingesting
            if getattr(settings, "discovery_enabled", True):
                try:
                    disc_res = svc.discover_sources(
                        max_sources=getattr(settings, "discovery_max_sources_per_run", 10),
                        max_urls_per_source=getattr(settings, "discovery_max_urls_per_source", 50),
                        ingest_discovered=False,
                    )
                    summary["discovery_discovered"] = disc_res.get("urls_discovered", 0)
                    summary["discovery_ingested"] = disc_res.get("documents_ingested", 0)
                    if disc_res.get("errors"):
                        summary["errors"].extend(disc_res["errors"])
                except Exception as e:
                    summary["errors"].append(f"Discovery phase error: {e}")
                    logger.exception("Error during scheduled discovery phase")

            # Phase 2: Ingest registered approved sources & newly discovered cross-portal links
            try:
                web_job = svc.run_ingestion(
                    max_pages=self.max_pages,
                    resolve_dns=False,
                    enable_discovery=True,
                )
                summary["web_discovered"] = web_job.documents_discovered
                summary["web_ingested"] = web_job.documents_ingested
                summary["web_unchanged"] = web_job.documents_unchanged
                if web_job.errors:
                    summary["errors"].extend(web_job.errors)
                self.last_job_id = web_job.job_id
            except Exception as e:
                summary["errors"].append(f"Web crawl phase error: {e}")
                logger.exception("Error during scheduled web crawl phase")

            # Phase 3: Local documents (PDFs in data/source_documents/)
            try:
                local_job = svc.ingest_local_documents()
                summary["local_ingested"] = local_job.documents_ingested
                summary["local_unchanged"] = local_job.documents_unchanged
                if local_job.errors:
                    summary["errors"].extend(local_job.errors)
            except Exception as e:
                summary["errors"].append(f"Local document ingestion error: {e}")
                logger.exception("Error during scheduled local document ingestion")

            if summary["errors"]:
                if summary["web_ingested"] > 0 or summary["local_ingested"] > 0 or summary["discovery_ingested"] > 0 or summary["web_unchanged"] > 0:
                    summary["status"] = "completed_with_errors"
                else:
                    summary["status"] = "failed"
            else:
                summary["status"] = "success"
            self.last_job_summary = summary
            logger.info("Automated periodic ingestion finished with status '%s': %s", summary["status"], summary)
            return summary
        except Exception as e:
            logger.exception("Fatal error during automated background ingestion run")
            summary["status"] = "error"
            summary["message"] = str(e)
            self.last_job_summary = summary
            return summary
        finally:
            self.is_running = False
            if not summary.get("skipped_due_to_overlap"):
                self.next_run_at = time.time() + (self.interval_hours * 3600)
                self.persist_state()
            self._run_lock.release()

    async def _scheduler_loop(self):
        """Background loop that waits until next_run_at and triggers scheduled ingestion."""
        logger.info("Scheduler loop started. Next run at: %s (run_on_startup=%s)", self.next_run_at, self.run_on_startup)

        while self.is_active:
            now = time.time()
            if self.next_run_at is None:
                self.next_run_at = self.recalculate_next_run(now)
                self.persist_state()

            wait_seconds = max(0.0, self.next_run_at - now)

            # Wait in slices of up to 1.0 second so stop() cancels quickly
            while wait_seconds > 0 and self.is_active:
                sleep_chunk = min(1.0, wait_seconds)
                await asyncio.sleep(sleep_chunk)
                wait_seconds = max(0.0, self.next_run_at - time.time())

            if not self.is_active:
                break

            if self.enabled:
                logger.info("Scheduler triggering periodic background ingestion run...")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._execute_ingestion)
            else:
                logger.info("Scheduler triggered but auto_ingestion is disabled. Advancing next_run_at.")
                self.next_run_at = time.time() + (self.interval_hours * 3600)
                self.persist_state()


scheduler = AutoIngestionScheduler()
