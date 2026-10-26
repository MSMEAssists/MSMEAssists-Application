import asyncio
import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from app.db.repository import SQLiteRepository
from app.models.entities import ProcessingJob, new_id, now_ts
from app.services.scheduler import AutoIngestionScheduler


class TestAutoIngestionScheduler(unittest.TestCase):
    def test_scheduler_default_config_and_lifecycle(self):
        """Verify default 24-hour interval, status reporting, and lifecycle."""
        async def _test():
            with tempfile.TemporaryDirectory() as tmpdir:
                repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
                scheduler = AutoIngestionScheduler(repository=repo)

                status = scheduler.get_status()
                self.assertTrue(status["enabled"])
                self.assertEqual(status["interval_hours"], 24)
                self.assertFalse(status["is_active"])
                self.assertFalse(status["is_currently_running_job"])
                self.assertIn("next_run_at", status)
                self.assertIn("run_on_startup", status)

                await scheduler.start()
                self.assertTrue(scheduler.is_active)

                # Calling start() again should be a no-op (no duplicate task spawned)
                task_id = id(scheduler._task)
                await scheduler.start()
                self.assertEqual(id(scheduler._task), task_id)

                await scheduler.stop()
                self.assertFalse(scheduler.is_active)
                self.assertIsNone(scheduler._task)

        asyncio.run(_test())

    def test_configurable_interval(self):
        """Verify that the update interval is configurable and recalculates next_run_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)
            scheduler.run_on_startup = False
            base_time = 1000000.0

            scheduler.last_run_at = base_time
            scheduler.interval_hours = 24
            next_run = scheduler.recalculate_next_run(now=base_time + 3600)
            self.assertEqual(next_run, base_time + (24 * 3600))

            # Reconfigure interval to 12 hours
            status = scheduler.configure(interval_hours=12)
            self.assertEqual(status["interval_hours"], 12)
            self.assertEqual(scheduler.interval_hours, 12)

    def test_startup_behavior_when_disabled(self):
        """When run_on_startup is False, first run is scheduled after the full interval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)
            scheduler.run_on_startup = False
            scheduler.last_run_at = None
            scheduler.interval_hours = 24

            now = 2000000.0
            next_run = scheduler.recalculate_next_run(now=now)
            self.assertEqual(next_run, now + (24 * 3600))

    def test_startup_behavior_when_enabled(self):
        """When run_on_startup is True, first run is scheduled after startup grace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)
            scheduler.run_on_startup = True
            scheduler.startup_grace_seconds = 5.0
            scheduler.last_run_at = None

            now = 2000000.0
            next_run = scheduler.recalculate_next_run(now=now)
            self.assertEqual(next_run, now + 5.0)

    def test_duplicate_job_and_overlap_prevention(self):
        """Ensure overlapping runs are rejected when an ingestion is already executing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)

            # Case 1: is_running is True -> run_now rejects
            scheduler.is_running = True
            async def _test_run_now():
                res = await scheduler.run_now()
                self.assertEqual(res["status"], "error")
                self.assertIn("already running", res["message"])
            asyncio.run(_test_run_now())
            scheduler.is_running = False

            # Case 2: _run_lock already acquired -> _execute_ingestion rejects
            acquired = scheduler._run_lock.acquire(blocking=False)
            self.assertTrue(acquired)
            try:
                second_res = scheduler._execute_ingestion()
                self.assertEqual(second_res["status"], "error")
                self.assertIn("already running", second_res["message"])
            finally:
                scheduler._run_lock.release()

            # Case 3: Another job is marked 'running' in the database
            active_job = ProcessingJob(job_id=new_id("job"), source_id=None, status="running", started_at=time.time())
            repo.upsert_job(active_job)
            third_res = scheduler._execute_ingestion()
            self.assertEqual(third_res["status"], "error")
            self.assertIn("already running", third_res["message"])

    def test_persistence_and_restart_recalculation(self):
        """Ensure next scheduled run is persisted and correctly recalculated across app restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state_test.db")
            repo = SQLiteRepository(path=db_path)

            now = time.time()
            ten_hours_ago = now - (10 * 3600)

            # Scheduler 1: Run completes and persists state
            scheduler1 = AutoIngestionScheduler(repository=repo)
            scheduler1.last_run_at = ten_hours_ago
            scheduler1.interval_hours = 24
            scheduler1.run_on_startup = False
            scheduler1.last_job_id = "job_123"
            scheduler1.last_job_summary = {"status": "success", "web_ingested": 5}
            scheduler1.persist_state()

            # Verify saved in SQLite system_state
            saved = repo.get_system_state("scheduler_state")
            self.assertIsNotNone(saved)
            self.assertEqual(saved["last_job_id"], "job_123")

            # Scheduler 2: Simulates application restart with new scheduler instance
            scheduler2 = AutoIngestionScheduler(repository=repo)
            self.assertEqual(scheduler2.last_job_id, "job_123")
            self.assertEqual(scheduler2.last_run_at, ten_hours_ago)

            # Recalculated next_run_at must be 14 hours in future (ten_hours_ago + 24h),
            # NOT reset to now + 24h
            expected_next = ten_hours_ago + (24 * 3600)
            self.assertAlmostEqual(scheduler2.next_run_at, expected_next, delta=5.0)

    def test_failed_ingestion_recovery(self):
        """Ensure individual source or ingestion errors do not crash the scheduler or prevent future runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)
            scheduler.interval_hours = 24

            dummy_local = ProcessingJob(job_id="test_loc", source_id=None, status="completed", started_at=time.time())
            with patch("app.services.ingestion_service.IngestionService.discover_sources", return_value={"status": "completed", "urls_discovered": 0, "documents_ingested": 0}), \
                 patch("app.services.ingestion_service.IngestionService.run_ingestion", side_effect=ConnectionError("Connection refused by remote host")), \
                 patch("app.services.ingestion_service.IngestionService.ingest_local_documents", return_value=dummy_local):
                summary = scheduler._execute_ingestion()

            # Verify scheduler completed cycle gracefully without uncaught exception
            self.assertFalse(scheduler.is_running)
            self.assertIsNotNone(scheduler.next_run_at)
            self.assertGreater(scheduler.next_run_at, time.time())
            self.assertIsNotNone(scheduler.last_job_summary)
            self.assertTrue(any("Connection refused" in err for err in summary.get("errors", [])))
            # Run lock was properly released
            self.assertTrue(scheduler._run_lock.acquire(blocking=False))
            scheduler._run_lock.release()

    def test_reuse_of_discovery_and_ingestion_pipeline(self):
        """Verify that _execute_ingestion calls the existing discovery and ingestion services."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)

            mock_disc_result = {"status": "completed", "urls_discovered": 12, "documents_ingested": 0}
            mock_web_job = ProcessingJob(job_id="test_web", source_id=None, status="completed", started_at=time.time(), documents_discovered=10, documents_ingested=2, documents_unchanged=8)
            mock_local_job = ProcessingJob(job_id="test_loc", source_id=None, status="completed", started_at=time.time(), documents_ingested=1, documents_unchanged=2)

            with patch("app.services.ingestion_service.IngestionService.discover_sources", return_value=mock_disc_result) as mock_disc, \
                 patch("app.services.ingestion_service.IngestionService.run_ingestion", return_value=mock_web_job) as mock_web, \
                 patch("app.services.ingestion_service.IngestionService.ingest_local_documents", return_value=mock_local_job) as mock_local:

                summary = scheduler._execute_ingestion()

                self.assertEqual(summary["status"], "success")
                self.assertEqual(summary["discovery_discovered"], 12)
                self.assertEqual(summary["discovery_ingested"], 0)
                self.assertEqual(summary["web_ingested"], 2)
                self.assertEqual(summary["web_unchanged"], 8)
                self.assertEqual(summary["local_ingested"], 1)

                mock_disc.assert_called_once()
                # Phase 1 discovery must not crawl/index duplicate pages before Phase 2
                self.assertFalse(mock_disc.call_args.kwargs.get("ingest_discovered", True))
                mock_web.assert_called_once()
                mock_local.assert_called_once()

    def test_single_cycle_no_duplicate_ingestion(self):
        """Ensure scheduled discovery and ingestion do not run twice in one cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)

            with patch("app.services.ingestion_service.IngestionService.discover_sources", return_value={"status": "completed", "urls_discovered": 5}) as mock_disc, \
                 patch("app.services.ingestion_service.IngestionService.run_ingestion", return_value=ProcessingJob(job_id="j1", source_id=None, status="completed", started_at=time.time())) as mock_web, \
                 patch("app.services.ingestion_service.IngestionService.ingest_local_documents", return_value=ProcessingJob(job_id="j2", source_id=None, status="completed", started_at=time.time())):
                summary = scheduler._execute_ingestion()

                # Phase 1 discovery ran with ingest_discovered=False
                mock_disc.assert_called_once()
                self.assertEqual(mock_disc.call_args.kwargs.get("ingest_discovered"), False)
                # Phase 2 ran once for all sources
                mock_web.assert_called_once()

    def test_running_job_in_repo_reschedules_short_retry(self):
        """When an external job is running in repo, scheduler skips and retries in 5 minutes (not 24 hours)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)
            scheduler.interval_hours = 24

            # Insert an active running job into repo
            active_job = ProcessingJob(job_id="active_1", source_id=None, status="running", started_at=time.time() - 100)
            repo.upsert_job(active_job)

            summary = scheduler._execute_ingestion()

            self.assertEqual(summary["status"], "error")
            self.assertTrue(summary.get("skipped_due_to_overlap"))
            self.assertIn("already running", summary["message"])
            self.assertIsNotNone(scheduler.last_job_summary)
            self.assertEqual(scheduler.last_job_summary["status"], "error")
            # Next run must be within ~300s (5 minutes), NOT 24 hours (86400s)
            now = time.time()
            self.assertLess(scheduler.next_run_at - now, 400)
            self.assertGreater(scheduler.next_run_at - now, 200)

    def test_error_reporting_accuracy(self):
        """Scheduler accurately reports 'completed_with_errors' when errors exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            scheduler = AutoIngestionScheduler(repository=repo)

            mock_web_job = ProcessingJob(
                job_id="j_err", source_id=None, status="completed", started_at=time.time(),
                documents_discovered=5, documents_ingested=2, documents_unchanged=2,
                errors=["Failed fetching https://bad.gov.in: timeout"],
            )
            with patch("app.services.ingestion_service.IngestionService.discover_sources", return_value={"status": "completed", "urls_discovered": 0}), \
                 patch("app.services.ingestion_service.IngestionService.run_ingestion", return_value=mock_web_job), \
                 patch("app.services.ingestion_service.IngestionService.ingest_local_documents", return_value=ProcessingJob(job_id="j_loc", source_id=None, status="completed", started_at=time.time())):
                summary = scheduler._execute_ingestion()

                self.assertEqual(summary["status"], "completed_with_errors")
                self.assertEqual(len(summary["errors"]), 1)
                self.assertIn("bad.gov.in", summary["errors"][0])

    def test_manual_ingestion_blocked_when_scheduler_or_ingestion_active(self):
        """Verify mutual exclusion: manual ingestion fails when scheduler or another job is active."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.scheduler import scheduler

        client = TestClient(app)

        # 1. When scheduler.is_running is True
        scheduler.is_running = True
        try:
            resp_run = client.post("/api/ingestion/run", json={"source_id": "msme"})
            self.assertEqual(resp_run.status_code, 409)
            self.assertIn("already running", resp_run.json()["detail"])

            resp_local = client.post("/api/ingestion/local", json={})
            self.assertEqual(resp_local.status_code, 409)

            resp_disc = client.post("/api/discovery/run", json={"ingest_discovered": True})
            self.assertEqual(resp_disc.status_code, 409)
        finally:
            scheduler.is_running = False

    def test_scheduler_api_configure_and_status(self):
        """Verify scheduler configuration and status endpoints work via JSON body."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp_status = client.get("/api/scheduler/status")
        self.assertEqual(resp_status.status_code, 200)
        data = resp_status.json()
        self.assertIn("enabled", data)
        self.assertIn("interval_hours", data)
        self.assertIn("is_active", data)

        # Configure with JSON body
        resp_conf = client.post("/api/scheduler/configure", json={"interval_hours": 18, "enabled": True})
        self.assertEqual(resp_conf.status_code, 200)
        conf_data = resp_conf.json()
        self.assertEqual(conf_data["interval_hours"], 18)
        self.assertTrue(conf_data["enabled"])

    def test_reindex_changed_page_cleans_stale_vectors_and_provenance(self):
        """Updating a changed page purges old vectors and old provenance records."""
        from app.embeddings.embedding_service import EmbeddingService
        from app.models.entities import ContentFormat, RawFetchResult
        from app.services.ingestion_service import IngestionService
        from app.vectorstore.numpy_store import NumpyVectorStore
        from app.core.source_registry import DEFAULT_APPROVED_SOURCES

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            vstore = NumpyVectorStore(os.path.join(tmpdir, "vstore"))
            es = EmbeddingService(provider_name="tfidf_svd", dimensions=32)
            sources = list(DEFAULT_APPROVED_SOURCES)
            svc = IngestionService(repository=repo, vector_store=vstore, embedding_service=es, approved_sources=sources)

            url = "https://www.msme.gov.in/schemes/test-scheme"
            source = next(s for s in sources if s.source_id == "msme")

            # 1. Ingest Version 1
            html_v1 = b"<html><head><title>Test Scheme</title></head><body><h1>PMEGP Details</h1><p>Eligibility requirement 1</p></body></html>"
            raw_v1 = RawFetchResult(url=url, final_url=url, status_code=200, content_format=ContentFormat.HTML, raw_bytes=html_v1, fetched_at=time.time())
            svc.embedding_service.fit(["PMEGP Details Eligibility requirement 1"])
            outcome1 = svc._ingest_one(raw_v1, source)
            self.assertEqual(outcome1, "ingested")

            doc1 = repo.find_document_by_url(url)
            self.assertEqual(doc1["version"], 1)
            chunks_v1 = repo.list_chunks_for_document(doc1["document_id"])
            chunk_ids_v1 = [c["chunk_id"] for c in chunks_v1]
            prov_v1 = repo.list_provenance_for_document(doc1["document_id"])
            self.assertGreater(len(chunks_v1), 0)
            self.assertEqual(len(prov_v1), len(chunks_v1))
            self.assertEqual(vstore.count(), len(chunks_v1))

            # 2. Ingest Version 2 (Changed content)
            html_v2 = b"<html><head><title>Test Scheme Updated</title></head><body><h1>PMEGP Details Updated</h1><p>New subsidy details and different rules</p></body></html>"
            raw_v2 = RawFetchResult(url=url, final_url=url, status_code=200, content_format=ContentFormat.HTML, raw_bytes=html_v2, fetched_at=time.time() + 10)
            svc.embedding_service.fit(["PMEGP Details Updated New subsidy details and different rules"])
            outcome2 = svc._ingest_one(raw_v2, source)
            self.assertEqual(outcome2, "ingested")

            doc2 = repo.find_document_by_url(url)
            self.assertEqual(doc2["version"], 2)
            chunks_v2 = repo.list_chunks_for_document(doc2["document_id"])
            chunk_ids_v2 = [c["chunk_id"] for c in chunks_v2]
            prov_v2 = repo.list_provenance_for_document(doc2["document_id"])

            # Old chunk IDs must not exist in SQLite or VectorStore
            for old_id in chunk_ids_v1:
                self.assertNotIn(old_id, chunk_ids_v2)
                self.assertIsNone(repo.get_chunk(old_id))
            # Provenance records must only reference new chunks
            for p in prov_v2:
                self.assertIn(p["chunk_id"], chunk_ids_v2)
                self.assertNotIn(p["chunk_id"], chunk_ids_v1)
            # Vector store count matches new chunks count
            self.assertEqual(vstore.count(), len(chunks_v2))

    def test_fastapi_lifespan_lifecycle(self):
        """Verify scheduler starts on FastAPI startup and stops cleanly on shutdown."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.scheduler import scheduler

        with TestClient(app):
            self.assertTrue(scheduler.is_active)
            self.assertIsNotNone(scheduler._task)

        self.assertFalse(scheduler.is_active)
        self.assertIsNone(scheduler._task)


if __name__ == "__main__":
    unittest.main()
