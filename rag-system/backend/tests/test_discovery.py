import gzip
import io
import time
import unittest
from unittest.mock import MagicMock, patch

from app.collectors.discovery import (
    DiscoveredUrl,
    GovernmentDiscoveryService,
    RateLimiter,
    RobotsTxtManager,
    SitemapParser,
    is_scheme_or_policy_relevant,
)
from app.core.config import settings
from app.core.source_registry import (
    DEFAULT_APPROVED_SOURCES,
    derive_source_id,
    derive_source_name,
    create_discovered_source,
)
from app.core.url_validator import (
    is_allowed_government_hostname,
    validate_discovered_url,
    validate_url,
)
from app.db.repository import SQLiteRepository


class TestGovernmentDiscovery(unittest.TestCase):

    def setUp(self):
        self.rate_limiter = RateLimiter(default_delay=0.0)
        self.rate_limiter.enabled = False  # Keep tests fast

    # --- 1. SITEMAP PARSING TESTS ---

    def test_parse_direct_urlset_sitemap(self):
        sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://dcmsme.gov.in/schemes/pmegp-guidelines</loc>
                <lastmod>2024-03-01</lastmod>
            </url>
            <url>
                <loc>https://dcmsme.gov.in/schemes/credit-guarantee</loc>
                <lastmod>2024-03-05</lastmod>
            </url>
            <url>
                <loc>https://dcmsme.gov.in/gallery/photos</loc>
            </url>
        </urlset>"""

        parser = SitemapParser(self.rate_limiter)
        sub_sitemaps, urls = parser.parse_sitemap_content(sitemap_xml, "https://dcmsme.gov.in/sitemap.xml")

        self.assertEqual(len(sub_sitemaps), 0)
        self.assertEqual(len(urls), 3)
        self.assertEqual(urls[0]["loc"], "https://dcmsme.gov.in/schemes/pmegp-guidelines")
        self.assertEqual(urls[0]["lastmod"], "2024-03-01")
        self.assertEqual(urls[1]["loc"], "https://dcmsme.gov.in/schemes/credit-guarantee")

    def test_parse_sitemap_index(self):
        index_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap>
                <loc>https://msme.gov.in/sitemap-schemes.xml</loc>
            </sitemap>
            <sitemap>
                <loc>https://msme.gov.in/sitemap-policies.xml</loc>
            </sitemap>
        </sitemapindex>"""

        parser = SitemapParser(self.rate_limiter)
        sub_sitemaps, urls = parser.parse_sitemap_content(index_xml, "https://msme.gov.in/sitemap.xml")

        self.assertEqual(len(sub_sitemaps), 2)
        self.assertEqual(sub_sitemaps[0], "https://msme.gov.in/sitemap-schemes.xml")
        self.assertEqual(sub_sitemaps[1], "https://msme.gov.in/sitemap-policies.xml")
        self.assertEqual(len(urls), 0)

    def test_parse_gzip_sitemap(self):
        raw_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://champions.gov.in/msme-schemes</loc></url>
        </urlset>"""
        gzipped = gzip.compress(raw_xml)

        parser = SitemapParser(self.rate_limiter)
        sub_sitemaps, urls = parser.parse_sitemap_content(gzipped, "https://champions.gov.in/sitemap.xml.gz")
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0]["loc"], "https://champions.gov.in/msme-schemes")

    def test_parse_malformed_xml_regex_fallback(self):
        broken_xml = b"""<unclosed_tag>
            <loc>https://dgft.gov.in/schemes/export-promotion</loc>
            <loc>https://dgft.gov.in/sitemap-trade.xml</loc>
        </bad>"""
        parser = SitemapParser(self.rate_limiter)
        sub_sitemaps, urls = parser.parse_sitemap_content(broken_xml, "https://dgft.gov.in/sitemap.xml")
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0]["loc"], "https://dgft.gov.in/schemes/export-promotion")
        self.assertEqual(len(sub_sitemaps), 1)
        self.assertEqual(sub_sitemaps[0], "https://dgft.gov.in/sitemap-trade.xml")

    # --- 2. ROBOTS.TXT COMPLIANCE TESTS ---

    def test_robots_txt_sitemap_extraction_and_rules(self):
        robots_content = """User-agent: *
Disallow: /admin/
Disallow: /private/
Crawl-delay: 2

Sitemap: https://msme.gov.in/sitemap.xml
Sitemap: https://msme.gov.in/sitemap-schemes.xml
"""
        manager = RobotsTxtManager(self.rate_limiter)
        info = manager.get_robots_info("msme.gov.in", custom_content=robots_content)

        self.assertEqual(len(info.sitemaps), 2)
        self.assertIn("https://msme.gov.in/sitemap.xml", info.sitemaps)
        self.assertIn("https://msme.gov.in/sitemap-schemes.xml", info.sitemaps)
        self.assertEqual(info.crawl_delay, 2.0)

        # Disallow checks
        self.assertFalse(manager.can_fetch("https://msme.gov.in/admin/dashboard"))
        self.assertFalse(manager.can_fetch("https://msme.gov.in/private/data"))
        self.assertTrue(manager.can_fetch("https://msme.gov.in/schemes/pmegp"))

    # --- 3. URL VALIDATION & ALLOWLIST TESTS ---

    def test_validate_discovered_gov_in_domain(self):
        for url in [
            "https://champions.gov.in/schemes/support",
            "https://kviconline.gov.in/pmegp/pmegpweb/index.jsp",
            "https://industries.telangana.gov.in/incentives",
            "https://msme.nic.in/schemes",
        ]:
            val = validate_discovered_url(url, resolve_dns=False)
            self.assertTrue(val.is_valid, f"Failed for {url}: {val.reason}")
            self.assertIsNotNone(val.matched_source)

    def test_validate_verified_extra_domains(self):
        for url in [
            "https://www.sidbi.in/en/loans",
            "https://cgtmse.in/Default.aspx",
            "https://mudra.org.in/Offerings",
        ]:
            val = validate_discovered_url(url, resolve_dns=False)
            self.assertTrue(val.is_valid, f"Failed for {url}: {val.reason}")

    def test_reject_arbitrary_external_domains(self):
        for url in [
            "https://www.google.com/search?q=msme",
            "https://en.wikipedia.org/wiki/MSME",
            "https://www.fake-government-schemes.com/pmegp",
            "https://blogspot.com/schemes",
        ]:
            val = validate_discovered_url(url, resolve_dns=False)
            self.assertFalse(val.is_valid, f"Should reject arbitrary external domain: {url}")

    def test_reject_ssrf_and_private_ips(self):
        for url in [
            "http://127.0.0.1:8000/schemes",
            "http://localhost:8000/schemes",
            "http://10.0.0.1/schemes",
            "http://192.168.1.50/schemes",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
        ]:
            val = validate_discovered_url(url, resolve_dns=False)
            self.assertFalse(val.is_valid, f"Should reject SSRF target: {url}")

    # --- 4. RELEVANCE FILTERING TESTS ---

    def test_relevance_detection(self):
        self.assertTrue(is_scheme_or_policy_relevant("https://dcmsme.gov.in/schemes/pmegp"))
        self.assertTrue(is_scheme_or_policy_relevant("https://sidbi.in/en/loans/credit-support"))
        self.assertTrue(is_scheme_or_policy_relevant("https://msme.gov.in/subsidies/capital-subsidy"))
        self.assertTrue(is_scheme_or_policy_relevant("https://gov.in/policies/msme-policy-2024"))
        self.assertTrue(is_scheme_or_policy_relevant("https://portal.gov.in/page", text="Credit Guarantee Scheme"))

        # Non-relevant pages
        self.assertFalse(is_scheme_or_policy_relevant("https://msme.gov.in/login"))
        self.assertFalse(is_scheme_or_policy_relevant("https://msme.gov.in/gallery/photos"))
        self.assertFalse(is_scheme_or_policy_relevant("https://msme.gov.in/careers/vacancy"))
        self.assertFalse(is_scheme_or_policy_relevant("https://msme.gov.in/feedback"))

    # --- 5. SOURCE REGISTRATION & DEDUPLICATION TESTS ---

    def test_source_registration_and_deduplication(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            service = GovernmentDiscoveryService(repository=repo, rate_limiter=self.rate_limiter)

            # 1. Register a new government portal
            src1 = service.register_or_get_source("https://champions.gov.in/index.html")
            self.assertIsNotNone(src1)
            self.assertTrue(src1.source_id.startswith("gov_"))
            self.assertIn("champions.gov.in", src1.allowed_domains)

            sources_in_db = repo.list_sources()
            self.assertEqual(len(sources_in_db), 1)

            # 2. Re-registering the same domain should NOT duplicate
            src2 = service.register_or_get_source("https://www.champions.gov.in/schemes")
            self.assertEqual(src1.source_id, src2.source_id)
            self.assertEqual(len(repo.list_sources()), 1)

            # 3. Registering another distinct government domain
            src3 = service.register_or_get_source("https://kviconline.gov.in/pmegp")
            self.assertNotEqual(src1.source_id, src3.source_id)
            self.assertEqual(len(repo.list_sources()), 2)

    def test_cross_portal_discovery(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            service = GovernmentDiscoveryService(repository=repo, rate_limiter=self.rate_limiter)

            links = [
                "https://dcmsme.gov.in/schemes/internal",  # same host
                "https://www.sidbi.in/en/loans/credit",    # valid cross-portal
                "https://cgtmse.in/schemes/guarantee",    # valid cross-portal
                "https://twitter.com/msme",                # external - reject
                "https://wikipedia.org/wiki/MSME",        # external - reject
            ]

            new_sources, urls = service.discover_cross_portal_links(
                html_links=links,
                current_hostname="dcmsme.gov.in",
                resolve_dns=False,
            )

            source_hosts = [d for s in new_sources for d in s.allowed_domains]
            self.assertTrue(any("sidbi.in" in h for h in source_hosts))
            self.assertTrue(any("cgtmse.in" in h for h in source_hosts))

            url_links = [u.url for u in urls]
            self.assertIn("https://www.sidbi.in/en/loans/credit", url_links)
            self.assertIn("https://cgtmse.in/schemes/guarantee", url_links)
            self.assertNotIn("https://twitter.com/msme", url_links)

    # --- 6. INDEXING, RETRIEVAL & FAILURE ISOLATION TESTS ---

    def test_discovered_source_is_indexed_and_searchable(self):
        """Verify newly discovered sources have their content actually chunked, embedded,
        indexed in vector store, and retrieved through search with intact provenance."""
        import os
        import tempfile
        from app.embeddings.embedding_service import EmbeddingService
        from app.models.entities import ContentFormat, RawFetchResult, now_ts
        from app.retrieval.retriever import Retriever
        from app.services.ingestion_service import IngestionService
        from app.vectorstore.numpy_store import NumpyVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            vec_store = NumpyVectorStore(path=os.path.join(tmpdir, "vs"))
            embed_svc = EmbeddingService(dimensions=64)

            # Register a newly discovered government source
            disc_source = create_discovered_source("https://champions.gov.in/")
            repo.upsert_source(disc_source)

            ingestion_svc = IngestionService(
                repository=repo,
                vector_store=vec_store,
                embedding_service=embed_svc,
                approved_sources=[disc_source],
            )

            # Mock fetch result for a scheme page on the newly discovered portal
            html_content = (
                b"<html><head><title>Champions Portal MSME Support Scheme</title></head>"
                b"<body><h1>Champions MSME Financial Assistance</h1>"
                b"<p>The Champions Portal provides financial assistance and grievance redressal "
                b"for micro and small enterprises across India. Under this scheme, eligible units "
                b"receive technological upgrading grants up to Rs 50 Lakhs.</p></body></html>"
            )
            raw = RawFetchResult(
                url="https://champions.gov.in/schemes/msme-support",
                final_url="https://champions.gov.in/schemes/msme-support",
                status_code=200,
                content_format=ContentFormat.HTML,
                raw_bytes=html_content,
                fetched_at=now_ts(),
            )

            # Pass through ingestion pipeline
            text = ingestion_svc._extract_and_clean_text_only(raw)
            embed_svc.fit([text])
            outcome = ingestion_svc._ingest_one(raw, disc_source)
            vec_store.persist()

            self.assertEqual(outcome, "ingested")
            self.assertEqual(len(repo.list_documents()), 1)
            self.assertGreater(vec_store.count(), 0)

            # Verify provenance carries the discovered portal URL and organization
            prov_records = repo.list_provenance_for_document(repo.list_documents()[0]["document_id"])
            self.assertGreater(len(prov_records), 0)
            self.assertEqual(prov_records[0]["official_url"], "https://champions.gov.in/schemes/msme-support")
            self.assertIn("champions.gov.in", prov_records[0]["source_name"])

            # Verify the newly indexed content is immediately retrievable
            retriever = Retriever(repository=repo, vector_store=vec_store, embedding_service=embed_svc)
            results = retriever.search("Champions financial assistance grants", top_k=3, similarity_threshold=0.0)

            self.assertGreater(len(results), 0)
            top = results[0]
            self.assertEqual(top.official_url, "https://champions.gov.in/schemes/msme-support")
            self.assertIn("Champions", top.title)

    def test_duplicate_prevention_on_reingestion(self):
        """Verify that ingesting the exact same content does not create duplicate documents or chunks."""
        import os
        import tempfile
        from app.embeddings.embedding_service import EmbeddingService
        from app.models.entities import ContentFormat, RawFetchResult, now_ts
        from app.services.ingestion_service import IngestionService
        from app.vectorstore.numpy_store import NumpyVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            vec_store = NumpyVectorStore(path=os.path.join(tmpdir, "vs"))
            embed_svc = EmbeddingService(dimensions=64)

            disc_source = create_discovered_source("https://champions.gov.in/")
            repo.upsert_source(disc_source)

            ingestion_svc = IngestionService(
                repository=repo,
                vector_store=vec_store,
                embedding_service=embed_svc,
                approved_sources=[disc_source],
            )

            raw = RawFetchResult(
                url="https://champions.gov.in/schemes/msme-support",
                final_url="https://champions.gov.in/schemes/msme-support",
                status_code=200,
                content_format=ContentFormat.HTML,
                raw_bytes=b"<html><body><h1>MSME Grant</h1><p>Support scheme details.</p></body></html>",
                fetched_at=now_ts(),
            )

            embed_svc.fit(["MSME Grant Support scheme details"])
            outcome1 = ingestion_svc._ingest_one(raw, disc_source)
            vec_store.persist()
            self.assertEqual(outcome1, "ingested")
            initial_doc_count = len(repo.list_documents())
            initial_vector_count = vec_store.count()

            # Second ingestion of unchanged bytes
            outcome2 = ingestion_svc._ingest_one(raw, disc_source)
            self.assertEqual(outcome2, "unchanged")
            self.assertEqual(len(repo.list_documents()), initial_doc_count)
            self.assertEqual(vec_store.count(), initial_vector_count)

    def test_graceful_failure_isolation_on_source_error(self):
        """Verify that a failing source does not stop the ingestion run for other sources."""
        import os
        import tempfile
        from unittest.mock import patch
        from app.embeddings.embedding_service import EmbeddingService
        from app.models.entities import ContentFormat, RawFetchResult, now_ts
        from app.services.ingestion_service import IngestionService
        from app.vectorstore.numpy_store import NumpyVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            vec_store = NumpyVectorStore(path=os.path.join(tmpdir, "vs"))
            embed_svc = EmbeddingService(dimensions=64)

            good_source = create_discovered_source("https://good.gov.in/")
            bad_source = create_discovered_source("https://bad.gov.in/")
            repo.upsert_source(good_source)
            repo.upsert_source(bad_source)

            ingestion_svc = IngestionService(
                repository=repo,
                vector_store=vec_store,
                embedding_service=embed_svc,
                approved_sources=[bad_source, good_source],
            )

            def mock_collect(source, *args, **kwargs):
                if source.source_id == bad_source.source_id:
                    raise ConnectionError("Server connection timed out")
                return [
                    RawFetchResult(
                        url="https://good.gov.in/schemes",
                        final_url="https://good.gov.in/schemes",
                        status_code=200,
                        content_format=ContentFormat.HTML,
                        raw_bytes=b"<html><body><h1>Good Scheme</h1><p>Active government scheme.</p></body></html>",
                        fetched_at=now_ts(),
                    )
                ]

            with patch("app.services.ingestion_service.collect_from_source", side_effect=mock_collect):
                job = ingestion_svc.run_ingestion(resolve_dns=False, enable_discovery=False)

            self.assertEqual(job.status, "completed")
            self.assertEqual(job.documents_ingested, 1)
            self.assertTrue(any("bad.gov.in" in err or "Server connection timed out" in err for err in job.errors))

    def test_api_endpoints_with_newly_discovered_content_and_manual_ingestion(self):
        """Verify that newly indexed content from discovered sources is available
        via /api/retrieval/search and /api/rag/query, and that manual ingestion works."""
        import os
        import tempfile
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.api.deps import (
            get_approved_sources, get_embedding_service_dep,
            get_ingestion_service, get_query_service, get_repo,
            get_vector_store_dep,
        )
        from app.embeddings.embedding_service import EmbeddingService
        from app.main import app
        from app.models.entities import ContentFormat, RawFetchResult, now_ts
        from app.services.ingestion_service import IngestionService
        from app.services.query_service import QueryService
        from app.vectorstore.numpy_store import NumpyVectorStore

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(path=os.path.join(tmpdir, "test.db"))
            vec_store = NumpyVectorStore(path=os.path.join(tmpdir, "vs"))
            embed_svc = EmbeddingService(dimensions=64)

            disc_source = create_discovered_source("https://champions.gov.in/")
            repo.upsert_source(disc_source)

            ingestion_svc = IngestionService(
                repository=repo,
                vector_store=vec_store,
                embedding_service=embed_svc,
                approved_sources=[disc_source],
            )
            query_svc = QueryService(
                repository=repo,
                vector_store=vec_store,
                embedding_service=embed_svc,
                llm_client=None,
            )

            # Ingest content from the newly discovered government source
            raw = RawFetchResult(
                url="https://champions.gov.in/schemes/msme-support",
                final_url="https://champions.gov.in/schemes/msme-support",
                status_code=200,
                content_format=ContentFormat.HTML,
                raw_bytes=b"<html><body><h1>Champions Portal MSME Support</h1><p>Financial assistance and technology upgradation support for small manufacturing enterprises.</p></body></html>",
                fetched_at=now_ts(),
            )
            embed_svc.fit(["Champions Portal MSME Support Financial assistance and technology upgradation support for small manufacturing enterprises."])
            outcome = ingestion_svc._ingest_one(raw, disc_source)
            vec_store.persist()
            self.assertEqual(outcome, "ingested")

            # Configure FastAPI dependency overrides
            app.dependency_overrides[get_repo] = lambda: repo
            app.dependency_overrides[get_vector_store_dep] = lambda: vec_store
            app.dependency_overrides[get_embedding_service_dep] = lambda: embed_svc
            app.dependency_overrides[get_approved_sources] = lambda: [disc_source]
            app.dependency_overrides[get_ingestion_service] = lambda: ingestion_svc
            app.dependency_overrides[get_query_service] = lambda: query_svc

            from app.services.scheduler import scheduler

            try:
                with patch.object(scheduler, "start"), patch.object(scheduler, "stop"):
                    client = TestClient(app)

                    # 1. Test POST /api/retrieval/search retrieves the newly discovered & indexed content
                search_resp = client.post(
                    "/api/retrieval/search",
                    json={
                        "query": "Champions MSME assistance support",
                        "top_k": 3,
                        "similarity_threshold": 0.0,
                    },
                )
                self.assertEqual(search_resp.status_code, 200)
                search_data = search_resp.json()
                self.assertGreater(len(search_data), 0)
                first_result = search_data[0]
                self.assertEqual(first_result["official_url"], "https://champions.gov.in/schemes/msme-support")
                self.assertIn("government", first_result["source_organization"].lower())
                self.assertIn("Champions", first_result["title"])

                # 2. Test POST /api/rag/query generates answer with provenance from discovered source
                rag_resp = client.post(
                    "/api/rag/query",
                    json={
                        "query": "What is the Champions MSME support scheme?",
                        "top_k": 3,
                        "similarity_threshold": 0.0,
                    },
                )
                self.assertEqual(rag_resp.status_code, 200)
                rag_data = rag_resp.json()
                self.assertTrue(rag_data["has_sufficient_context"])
                self.assertGreater(len(rag_data["citations"]), 0)
                self.assertEqual(rag_data["citations"][0]["official_url"], "https://champions.gov.in/schemes/msme-support")
                self.assertIn("Champions Portal MSME Support", rag_data["answer_text"])

                # 3. Test POST /api/ingestion/run (Manual ingestion endpoint)
                with patch("app.services.ingestion_service.collect_from_source", return_value=[raw]):
                    ingest_resp = client.post(
                        "/api/ingestion/run",
                        json={"source_id": disc_source.source_id, "max_pages": 5},
                    )
                    self.assertEqual(ingest_resp.status_code, 200)
                    ingest_data = ingest_resp.json()
                    self.assertEqual(ingest_data["status"], "completed")
                    self.assertEqual(ingest_data["source_id"], disc_source.source_id)

            finally:
                app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()

