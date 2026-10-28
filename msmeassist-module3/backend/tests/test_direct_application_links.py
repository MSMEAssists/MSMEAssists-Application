"""
Unit tests for direct application link audit & implementation in Module 3.
Validates:
1. Grounded scheme-link mappings for fallback schemes.
2. clean_direct_application_url rejects generic homepages, PDFs, and invalid links.
3. Ranking items carry direct application URLs or None.
4. Correct association is maintained across CandidateScheme and BtlRankingItem.
"""
import pytest
from app.models.schemas import CandidateScheme, BtlRankingItem, PairwiseComparison
from app.services.rag_client import FALLBACK_SCHEMES, clean_direct_application_url
from app.services.explainability import ExplainabilityEngine


def test_fallback_schemes_grounded_application_links():
    schemes_by_id = {s.id: s for s in FALLBACK_SCHEMES}

    # PMEGP: Verified online direct application e-portal
    assert "pmegp_subsidy" in schemes_by_id
    pmegp = schemes_by_id["pmegp_subsidy"]
    assert pmegp.official_application_url in (
        "https://pmegp.msme.gov.in/Home/Homepage",
        "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp",
    )
    assert pmegp.official_url == "https://msme.gov.in/pmegp"

    # ZED: Verified online direct registration portal
    assert "msme_champions_zed" in schemes_by_id
    zed = schemes_by_id["msme_champions_zed"]
    assert zed.official_application_url == "https://zed.msme.gov.in/account/register"

    # Stand-Up India: Verified online applicant registration
    assert "stand_up_india" in schemes_by_id
    sui = schemes_by_id["stand_up_india"]
    assert sui.official_application_url == "https://www.standupmitra.in/Login/Register"

    # CGTMSE: Credit guarantee applied via Member Lending Institutions (Banks) -- no direct online application
    assert "cgtmse_credit" in schemes_by_id
    cgtmse = schemes_by_id["cgtmse_credit"]
    assert cgtmse.official_application_url is None
    assert cgtmse.official_url == "https://www.cgtmse.in/"

    # MUDRA: Refinanced via commercial banks/RRBs -- no direct online application form on mudra.org.in
    assert "mudra_kishore_tarun" in schemes_by_id
    mudra = schemes_by_id["mudra_kishore_tarun"]
    assert mudra.official_application_url is None
    assert mudra.official_url == "https://www.mudra.org.in/"


def test_clean_direct_application_url_validation():
    # Valid online portals
    assert clean_direct_application_url(
        "https://pmegp.msme.gov.in/Home/Homepage"
    ) == "https://pmegp.msme.gov.in/Home/Homepage"
    assert clean_direct_application_url(
        "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"
    ) == "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"
    assert clean_direct_application_url(
        "https://zed.msme.gov.in/account/register"
    ) == "https://zed.msme.gov.in/account/register"
    assert clean_direct_application_url(
        "https://www.standupmitra.in/Login/Register"
    ) == "https://www.standupmitra.in/Login/Register"

    # Generic homepages and information listings must be rejected
    assert clean_direct_application_url("https://msme.gov.in/") is None
    assert clean_direct_application_url("https://www.msme.gov.in") is None
    assert clean_direct_application_url("https://www.msme.gov.in/offerings/schemes-and-services") is None
    assert clean_direct_application_url("https://msme.gov.in/pmegp") is None
    assert clean_direct_application_url("https://www.cgtmse.in/") is None
    assert clean_direct_application_url("https://www.cgtmse.in") is None
    assert clean_direct_application_url("https://www.mudra.org.in/") is None
    assert clean_direct_application_url("https://www.sidbi.in/en/") is None
    assert clean_direct_application_url("https://doe.gov.in/") is None
    assert clean_direct_application_url("https://mca.gov.in/") is None

    # PDFs and documents must be rejected
    assert clean_direct_application_url("https://msme.gov.in/guidelines.pdf") is None
    assert clean_direct_application_url("https://cgtmse.in/circular.pdf") is None

    # None and empty
    assert clean_direct_application_url(None) is None
    assert clean_direct_application_url("") is None
    assert clean_direct_application_url("   ") is None


def test_assemble_rankings_preserves_application_url():
    engine = ExplainabilityEngine()

    candidates = [
        CandidateScheme(
            id="scheme_with_portal",
            title="Scheme With Portal",
            organization="Ministry of MSME",
            official_url="https://msme.gov.in/scheme",
            official_application_url="https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp",
            knowledge_type="SCHEME",
            snippet="Test snippet with application portal.",
        ),
        CandidateScheme(
            id="scheme_without_portal",
            title="Scheme Without Portal (Offline/Bank)",
            organization="Ministry of Finance",
            official_url="https://www.cgtmse.in/",
            official_application_url=None,
            knowledge_type="LOAN",
            snippet="Test snippet for offline bank guarantee scheme.",
        ),
    ]

    thetas = {"scheme_with_portal": 1.2, "scheme_without_portal": 0.8}
    probabilities = {"scheme_with_portal": 0.6, "scheme_without_portal": 0.4}
    pairwise_matrix = [[0.5, 0.65], [0.35, 0.5]]
    pairwise_results = [
        PairwiseComparison(
            scheme_a_id="scheme_with_portal",
            scheme_a_title="Scheme With Portal",
            scheme_b_id="scheme_without_portal",
            scheme_b_title="Scheme Without Portal (Offline/Bank)",
            winner_id="scheme_with_portal",
            preference_probability=0.65,
            comparative_rationale="Higher subsidy and direct online portal.",
        )
    ]
    global_attributions = {"manufacturing": 60.0, "micro": 40.0}

    ranked = engine.assemble_rankings(
        candidates=candidates,
        thetas=thetas,
        probabilities=probabilities,
        pairwise_matrix=pairwise_matrix,
        pairwise_results=pairwise_results,
        global_attributions=global_attributions,
    )

    assert len(ranked) == 2

    # First rank: scheme_with_portal
    assert ranked[0].scheme_id == "scheme_with_portal"
    assert ranked[0].official_application_url == "https://www.kviconline.gov.in/pmegpeportal/pmegphome/index.jsp"
    assert ranked[0].official_url == "https://msme.gov.in/scheme"

    # Second rank: scheme_without_portal (must be None)
    assert ranked[1].scheme_id == "scheme_without_portal"
    assert ranked[1].official_application_url is None
    assert ranked[1].official_url == "https://www.cgtmse.in/"
