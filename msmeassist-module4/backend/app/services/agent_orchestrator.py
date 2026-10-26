"""
Finance & Loan Advisory Agent Orchestrator for Module 4.

Orchestrates:
1. Profile & Financial Data Resolution (Module 1 Integration)
2. Financial Analysis & Risk Scoring (FinancialAnalyzer)
3. Loan Requirement Identification & Categorization (LoanAdvisor)
4. RAG Knowledge Retrieval for Loans & Schemes (RagIntegrationService)
5. Explainable Recommendation Consumption (Module 3 BTL Integration)
6. Eligibility Evaluation & Option Ranking
7. Explainable Financial Advisory Synthesis
"""
import logging
from typing import Optional
from app.models.schemas import (
    BusinessProfilePayload,
    FinancialInputs,
    LoanAdvisoryResponse,
    LoanInputs,
    LoanRecommendationRequest,
)
from app.services.financial_analyzer import FinancialAnalyzer
from app.services.loan_advisor import LoanAdvisor
from app.services.module1_client import Module1Client
from app.services.module3_integration import Module3IntegrationService
from app.services.rag_integration import RagIntegrationService

logger = logging.getLogger(__name__)


class FinanceLoanAgentOrchestrator:
    def __init__(
        self,
        financial_analyzer: Optional[FinancialAnalyzer] = None,
        loan_advisor: Optional[LoanAdvisor] = None,
        rag_integration: Optional[RagIntegrationService] = None,
        module3_integration: Optional[Module3IntegrationService] = None,
        module1_client: Optional[Module1Client] = None,
    ):
        self.financial_analyzer = financial_analyzer or FinancialAnalyzer()
        self.loan_advisor = loan_advisor or LoanAdvisor()
        self.rag_integration = rag_integration or RagIntegrationService()
        self.module3_integration = module3_integration or Module3IntegrationService()
        self.module1_client = module1_client or Module1Client()

    async def generate_loan_advisory(
        self,
        request: LoanRecommendationRequest,
        auth_token: Optional[str] = None,
    ) -> LoanAdvisoryResponse:
        # 1. Resolve Profile & Financial Inputs
        m1_profile, m1_fin = await self.module1_client.fetch_user_profile(auth_token)

        # Merge business profile: request payload takes precedence, fallback to Module 1, then defaults
        biz_profile = request.business_profile or m1_profile or BusinessProfilePayload()
        if m1_profile and request.business_profile:
            # fill missing fields from m1
            if request.business_profile.name == "MSME Enterprise" and m1_profile.name:
                biz_profile.name = m1_profile.name
            if m1_profile.msme_classification:
                biz_profile.msme_classification = m1_profile.msme_classification

        # Merge financial inputs: request payload takes precedence, fallback to Module 1
        fin_inputs = request.financial_inputs or FinancialInputs()
        if m1_fin:
            if fin_inputs.annual_turnover_inr is None:
                fin_inputs.annual_turnover_inr = m1_fin.annual_turnover_inr
            if fin_inputs.investment_requirement_inr is None:
                fin_inputs.investment_requirement_inr = m1_fin.investment_requirement_inr
            if fin_inputs.has_existing_loan is None:
                fin_inputs.has_existing_loan = m1_fin.has_existing_loan
            if fin_inputs.has_bank_finance is None:
                fin_inputs.has_bank_finance = m1_fin.has_bank_finance

        loan_inputs = request.loan_inputs or LoanInputs()

        # 2. Run Financial Analysis
        fin_analysis = self.financial_analyzer.analyze(fin_inputs, biz_profile)

        # 3. Identify Loan Requirement
        loan_req = self.loan_advisor.identify_loan_requirement(
            loan_inputs=loan_inputs,
            financial_summary=fin_analysis.financial_summary,
            financial_inputs=fin_inputs,
        )

        # 4. Retrieve RAG Loan & Financing Schemes
        query = (
            f"MSME loan financial scheme {loan_req.purpose} collateral free credit guarantee "
            f"{biz_profile.msme_classification} enterprise {biz_profile.state}"
        )
        rag_schemes = await self.rag_integration.retrieve_loan_schemes(query, top_k=request.top_k)

        # 5. Consume Module 3 Rankings if enabled
        module3_rankings = []
        if request.use_module3_rankings:
            profile_dict = {
                "business": {"name": biz_profile.name, "type": biz_profile.business_type, "industry": biz_profile.industry},
                "financial": {"annual_turnover_inr": fin_inputs.annual_turnover_inr, "msme_classification": biz_profile.msme_classification},
                "location": {"state": biz_profile.state},
            }
            module3_rankings = await self.module3_integration.get_ranked_recommendations(
                profile_dict=profile_dict, auth_token=auth_token, top_k=request.top_k
            )

        # 6. Evaluate Eligibility & Rank Options
        recommended_options = self.loan_advisor.evaluate_and_rank_loan_options(
            rag_schemes=rag_schemes,
            module3_rankings=module3_rankings,
            financial_summary=fin_analysis.financial_summary,
            loan_requirement=loan_req,
            profile=biz_profile,
        )

        # 7. Synthesize Explanation
        top_option = recommended_options[0].name if recommended_options else "MSME Government Loan Scheme"
        explanation = (
            f"Based on financial analysis of {biz_profile.name}, the business maintains a turnover of "
            f"{fin_analysis.financial_summary.annual_revenue} and a '{fin_analysis.financial_summary.repayment_capacity_rating}' "
            f"repayment capacity rating (DSCR: {fin_analysis.financial_summary.estimated_dscr}). "
            f"To address the estimated funding requirement of {loan_req.required_amount} for {loan_req.purpose}, "
            f"'{top_option}' is recommended as the top option due to matching turnover eligibility, "
            f"government guarantee cover, and competitive interest terms retrieved from official RAG records."
        )

        return LoanAdvisoryResponse(
            business_name=biz_profile.name or "MSME Enterprise",
            msme_classification=(biz_profile.msme_classification or "micro").capitalize(),
            financial_summary=fin_analysis.financial_summary,
            loan_requirement=loan_req,
            recommended_options=recommended_options,
            financial_risks=fin_analysis.financial_risks,
            missing_information=fin_analysis.missing_information,
            improvement_areas=fin_analysis.improvement_areas,
            explanation=explanation,
        )
