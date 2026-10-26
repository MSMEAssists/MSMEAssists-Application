"""
Module 1 Client Service for Module 4: Finance & Loan Agent.

Fetches authenticated user business and financial profiles from Module 1.
Maps Module 1 field names (investment_inr) to Module 4 schema (investment_requirement_inr).
"""
import logging
from typing import Optional, Tuple
import httpx

from app.core.config import get_finance_settings
from app.models.schemas import BusinessProfilePayload, FinancialInputs

logger = logging.getLogger(__name__)


class Module1Client:
    def __init__(self):
        self.settings = get_finance_settings()

    async def fetch_user_profile(
        self,
        auth_token: Optional[str] = None,
    ) -> Tuple[Optional[BusinessProfilePayload], Optional[FinancialInputs]]:
        """
        Retrieves user business and financial profile from Module 1.

        Returns (BusinessProfilePayload, FinancialInputs) or (None, None)
        if no token or lookup fails.
        """
        if not auth_token:
            return None, None

        # 1. Try internal DB access when running inside unified FastAPI app (Module 1 + Module 4 combined)
        try:
            from app.api.v1.deps import get_profile_repository  # Module 1 dep
            from app.db.mongo_client import get_database          # Module 1 db
            from app.core.security import decode_access_token     # Module 1 security

            clean_token = auth_token.replace("Bearer ", "").strip()
            payload = decode_access_token(clean_token)
            user_id = payload.get("sub")

            if user_id:
                db = get_database()
                profile_repo = get_profile_repository(db)
                profile_doc = await profile_repo.find_by_user_id(user_id)

                if profile_doc:
                    biz_data = profile_doc.business.dict() if profile_doc.business else {}
                    fin_data = profile_doc.financial.dict() if profile_doc.financial else {}
                    char_data = profile_doc.characteristics.dict() if profile_doc.characteristics else {}
                    loc_data = profile_doc.location.dict() if profile_doc.location else {}

                    # Calculate business age
                    biz_age = 3.0
                    if profile_doc.business and getattr(profile_doc.business, "established_date", None):
                        from datetime import datetime, timezone
                        now = datetime.now(timezone.utc)
                        est = profile_doc.business.established_date
                        if est.tzinfo is None:
                            est = est.replace(tzinfo=timezone.utc)
                        biz_age = max((now - est).days / 365.25, 0.5)

                    biz_profile = BusinessProfilePayload(
                        name=biz_data.get("name", "Your Enterprise"),
                        business_type=biz_data.get("type", "manufacturing"),
                        industry=biz_data.get("industry", "General Industry"),
                        sub_sector=biz_data.get("sub_sector"),
                        business_age_years=round(biz_age, 1),
                        msme_classification=fin_data.get("msme_classification", "micro"),
                        state=loc_data.get("state", "India"),
                        district=loc_data.get("district"),
                        is_women_owned=char_data.get("is_women_owned", False),
                        social_category=char_data.get("social_category", "general"),
                        is_rural_enterprise=char_data.get("is_rural_enterprise", False),
                        is_startup_recognized=char_data.get("is_startup_recognized", False),
                    )

                    # Module 1 uses investment_inr; Module 4 schema uses investment_requirement_inr
                    fin_inputs = FinancialInputs(
                        annual_turnover_inr=fin_data.get("annual_turnover_inr"),
                        investment_requirement_inr=fin_data.get("investment_inr"),
                        has_existing_loan=fin_data.get("has_existing_loan"),
                        has_bank_finance=fin_data.get("has_bank_finance"),
                        profitability_status=fin_data.get("profitability_status"),
                    )

                    return biz_profile, fin_inputs
        except Exception as exc:
            logger.debug(f"In-process Module 1 lookup failed ({exc}); falling back to HTTP.")

        # 2. Try HTTP call to Module 1 /api/profile/me endpoint
        url = f"{self.settings.module1_service_url.rstrip('/')}/api/profile/me"
        auth_header = auth_token if auth_token.startswith("Bearer ") else f"Bearer {auth_token}"
        headers = {"Authorization": auth_header}

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    biz = data.get("business") or {}
                    fin = data.get("financial") or {}
                    char = data.get("characteristics") or {}
                    loc = data.get("location") or {}

                    biz_profile = BusinessProfilePayload(
                        name=biz.get("name", "Your Enterprise"),
                        business_type=biz.get("type", "manufacturing"),
                        industry=biz.get("industry", "General Industry"),
                        sub_sector=biz.get("sub_sector"),
                        msme_classification=fin.get("msme_classification", "micro"),
                        state=loc.get("state", "India"),
                        district=loc.get("district"),
                        is_women_owned=char.get("is_women_owned", False),
                        social_category=char.get("social_category", "general"),
                        is_rural_enterprise=char.get("is_rural_enterprise", False),
                        is_startup_recognized=char.get("is_startup_recognized", False),
                    )

                    # Module 1 HTTP response uses investment_inr; map to Module 4's investment_requirement_inr
                    fin_inputs = FinancialInputs(
                        annual_turnover_inr=fin.get("annual_turnover_inr"),
                        investment_requirement_inr=fin.get("investment_inr"),
                        has_existing_loan=fin.get("has_existing_loan"),
                        has_bank_finance=fin.get("has_bank_finance"),
                        profitability_status=fin.get("profitability_status"),
                    )

                    return biz_profile, fin_inputs
        except Exception as exc:
            logger.info(f"Module 1 HTTP profile lookup at {url} failed ({exc}); proceeding without profile data.")

        return None, None
