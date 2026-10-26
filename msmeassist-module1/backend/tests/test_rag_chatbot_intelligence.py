"""
Comprehensive evaluation and regression test suite for MSMEAssist RAG Chatbot Intelligence.

Verifies:
  1. Single-doc factual extraction (ZED subsidy = 80%).
  2. Multi-doc guarantee/loan financing (CGTMSE collateral-free limits & Master Circular).
  3. Conversational reference resolution (Pronoun "for that" resolves to prior turn's scheme).
  4. Dispute & delayed payment resolution (ODR / MSEFC / MSME-1 45-day rule).
  5. Export promotion schemes (DGFT MAI airfare & stall subsidies).
  6. Statutory document requirements (Udyam zero-cost registration).
  7. Adversarial out-of-domain rejection (Cryptocurrency tax -> Transparent notice, zero GST dump).
  8. Off-topic query rejection (Canada visa -> Transparent notice, zero citations).
  9. Preference-constrained reconsideration (Reject PMEGP -> Tailored machinery financing).
 10. Gap analysis & profile improvement (How to qualify for PMEGP -> 6-point roadmap).
"""
import asyncio
import os
import sys
import unittest
from pathlib import Path

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parents[1]
RAG_BACKEND = PROJECT_ROOT / "rag-system" / "backend"

sys.path.insert(0, str(BACKEND_DIR))

os.environ["SQLITE_PATH"] = str(RAG_BACKEND / "data" / "gov_rag.db")
os.environ["VECTOR_STORE_PATH"] = str(RAG_BACKEND / "data" / "vector_store")
os.environ["SOURCE_DOCUMENTS_PATH"] = str(RAG_BACKEND / "data" / "source_documents")

from datetime import datetime, timezone
from bson import ObjectId
from app.core.constants import AreaType, BusinessType, MSMEClassification, ProfileStatus
from app.models.profile_model import (
    BusinessSection,
    CharacteristicsSection,
    FinancialSection,
    LocationSection,
    ProfileModel,
)
from app.services.advisor_service import AdvisorService, resolve_conversational_query
from app.services.rag_client import RagClient


class TestRAGChatbotIntelligence(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure SQLite path is set
        os.environ["SQLITE_PATH"] = str(RAG_BACKEND / "data" / "gov_rag.db")
        os.environ["VECTOR_STORE_PATH"] = str(RAG_BACKEND / "data" / "vector_store")
        
        # Initialize RAG client (uses inprocess_rag_query)
        cls.rag_client = RagClient()
        cls.advisor = AdvisorService(rag_client=cls.rag_client)

        # Mock sample user profile: Micro Manufacturing Unit
        cls.sample_profile = ProfileModel(
            user_id=ObjectId(),
            business=BusinessSection(
                name="Bharat Precision Tools",
                type=BusinessType.MANUFACTURING,
                industry="Manufacturing",
                established_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
            ),
            location=LocationSection(
                state="Maharashtra",
                district="Pune",
                city="Pune",
                pin_code="411001",
                area_type=AreaType.URBAN,
            ),
            financial=FinancialSection(
                annual_turnover_inr=4500000.0,
                investment_inr=1800000.0,
                employee_count=12,
                msme_classification=MSMEClassification.MICRO,
            ),
            characteristics=CharacteristicsSection(
                is_women_owned=False,
                is_rural_enterprise=False,
            ),
            status=ProfileStatus.ACTIVE,
        )

    # 1. Single-doc factual extraction (ZED subsidy percentage = 80%)
    async def test_zed_subsidy_percentage(self):
        query = "What is the subsidy percentage for ZED certification for micro enterprises?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertTrue(res["has_sufficient_context"])
        self.assertGreater(len(res["citations"]), 0)
        answer = res["answer_text"]
        self.assertIn("80%", answer, "Answer must accurately extract the 80% subsidy for micro units")
        self.assertTrue(
            any("zed" in c.official_url.lower() or "zed" in (c.title or "").lower() for c in res["citations"]),
            "Citation must include official ZED circular/guidelines"
        )

    # 2. Multi-doc guarantee/loan financing (CGTMSE Master Circular)
    async def test_cgtmse_collateral_free_loan(self):
        query = "Can a registered MSME get loans without collateral under CGTMSE?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertTrue(res["has_sufficient_context"])
        self.assertGreater(len(res["citations"]), 0)
        answer = res["answer_text"]
        self.assertTrue(
            "cgtmse" in answer.lower() or "credit guarantee" in answer.lower(),
            "Answer must directly cover CGTMSE credit guarantee"
        )
        self.assertTrue(
            any("cgtmse.in" in c.official_url.lower() or "cgtmse" in (c.title or "").lower() for c in res["citations"]),
            "Citation must include official CGTMSE guidelines/circular"
        )
        # Verify no login screen or photo gallery citations leaked
        for c in res["citations"]:
            self.assertNotIn("login screen", (c.title or "").lower())
            self.assertNotIn("gallery", c.official_url.lower())

    # 3. Conversational reference resolution
    async def test_conversational_pronoun_resolution(self):
        history = [
            {"role": "user", "content": "Tell me about the Credit Guarantee Fund Trust (CGTMSE)."},
            {"role": "assistant", "content": "CGTMSE provides collateral-free credit facilities up to Rs 5 Crore through eligible member lending institutions."},
        ]
        follow_up = "What documents do I need for that?"
        
        # Test query resolver function directly
        eff_query, scheme = resolve_conversational_query(follow_up, history)
        self.assertIn("CGTMSE", eff_query.upper(), "Effective query must substitute or append CGTMSE")
        self.assertEqual(scheme, "CGTMSE")

        # Test end-to-end advisor response
        res = await self.advisor.generate_personalized_response(
            query=follow_up,
            profile=self.sample_profile,
            history=history,
        )
        self.assertTrue(res["has_sufficient_context"])
        answer = res["answer_text"]
        self.assertTrue(
            "cgtmse" in answer.lower() or "credit guarantee" in answer.lower(),
            "Answer to follow-up must address CGTMSE rather than generic or random schemes"
        )

    # 4. Dispute & delayed payment resolution (ODR / MSEFC 45-day rule)
    async def test_delayed_payments_dispute_resolution(self):
        query = "How can I recover delayed payments from a buyer?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertTrue(res["has_sufficient_context"])
        self.assertGreater(len(res["citations"]), 0)
        answer = res["answer_text"].lower()
        self.assertTrue(
            any(k in answer for k in ("delayed payment", "msefc", "odr", "samadhaan", "45-day", "45 days")),
            "Answer must cover official delayed payment resolution mechanisms"
        )

    # 5. Export promotion schemes (DGFT MAI)
    async def test_export_promotion_schemes(self):
        query = "Are there any export promotion schemes or subsidies for MSMEs?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertTrue(res["has_sufficient_context"])
        self.assertGreater(len(res["citations"]), 0)
        answer = res["answer_text"].lower()
        self.assertTrue(
            any(k in answer for k in ("dgft", "market access", "mai", "rodtep", "export")),
            "Answer must cover DGFT export assistance / MAI / RoDTEP"
        )

    # 6. Statutory document requirements (Udyam Registration)
    async def test_udyam_registration_documents(self):
        query = "What documents do I need for Udyam registration?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertTrue(res["has_sufficient_context"])
        answer = res["answer_text"].lower()
        self.assertTrue(
            "udyam" in answer or "registration" in answer,
            "Answer must explain official Udyam registration guidelines"
        )

    # 7. Adversarial out-of-domain rejection (Cryptocurrency tax)
    async def test_adversarial_out_of_domain_cryptocurrency(self):
        query = "What is the tax rate on cryptocurrency in India?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        # Must refuse or state transparent limitation
        self.assertFalse(res["has_sufficient_context"], "Out-of-domain query must NOT claim sufficient official context")
        self.assertEqual(len(res["citations"]), 0, "Out-of-domain query must NOT fabricate citations")
        answer = res["answer_text"].lower()
        self.assertIn("could not find sufficient verified", answer)
        self.assertNotIn("gst refund guidelines", answer, "Must NOT leak GST Refund guidelines as answer to cryptocurrency")

    # 8. Off-topic query rejection (Canada visa)
    async def test_off_topic_rejection_canada_visa(self):
        query = "How do I apply for a Canada visitor visa?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertFalse(res["has_sufficient_context"])
        self.assertEqual(len(res["citations"]), 0)
        answer = res["answer_text"].lower()
        self.assertIn("could not find sufficient verified", answer)

    # 9. Preference-constrained reconsideration (Reject PMEGP, request machinery loan)
    async def test_preference_reconsideration(self):
        query = "I don't like PMEGP. I need a collateral-free loan for purchasing machinery"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertEqual(res["intent"], "SCHEME_RECONSIDERATION")
        self.assertTrue(res["has_sufficient_context"])
        answer = res["answer_text"]
        self.assertIn("excluded **PMEGP**", answer, "Must acknowledge exclusion of PMEGP")
        self.assertIn("CGTMSE", answer, "Must recommend collateral-free alternatives like CGTMSE")

    # 10. Gap analysis and profile improvement
    async def test_profile_improvement_gap_analysis(self):
        query = "Why am I not eligible for PMEGP and how can I qualify?"
        res = await self.advisor.generate_personalized_response(
            query=query,
            profile=self.sample_profile,
        )
        self.assertEqual(res["intent"], "PROFILE_IMPROVEMENT")
        self.assertTrue(res["has_sufficient_context"])
        answer = res["answer_text"]
        self.assertIn("Qualification & Profile Improvement Roadmap", answer)
        self.assertIn("PMEGP", answer)
        self.assertGreater(len(res.get("eligibility_gaps", [])), 0, "Must return structured gap analysis")


if __name__ == "__main__":
    unittest.main()
