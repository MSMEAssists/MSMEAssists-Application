"""
Scheme Query Builder.

Constructs neutral, multi-faceted search queries from a normalized business profile
to retrieve candidate government schemes and official guidelines from the RAG service.
"""
from typing import List, Optional
from app.models.profile_model import ProfileModel


class SchemeQueryBuilder:
    """Generates targeted search queries spanning domain, scale, location, and demographic dimensions."""

    def build_queries(self, profile: Optional[ProfileModel]) -> List[str]:
        if not profile:
            return [
                "MSME government schemes credit subsidy financial assistance",
                "working capital credit guarantee and loan support",
                "cluster development and technology upgradation",
            ]

        queries: List[str] = []

        # 1. Sector & Industry Facet
        sector = profile.business.type.value if profile.business else "MSME"
        industry = profile.business.industry if profile.business else ""
        sub_sector = profile.business.sub_sector if (profile.business and profile.business.sub_sector) else ""
        
        sector_phrase = f"{sector} {industry} {sub_sector}".strip()
        queries.append(f"{sector_phrase} government schemes and financial assistance")
        queries.append(f"{sector_phrase} credit subsidy technology support")

        # 2. Scale & Classification Facet
        if profile.financial:
            classification = profile.financial.msme_classification.value if hasattr(profile.financial, 'msme_classification') else "micro"
            queries.append(f"{classification} enterprise loan subsidy grant support")
            queries.append(f"{classification} enterprise working capital and credit guarantee")

        # 3. Location & Regional Facet
        if profile.location:
            state = profile.location.state
            area = profile.location.area_type.value if hasattr(profile.location.area_type, 'value') else str(profile.location.area_type)
            queries.append(f"{state} {area} enterprise cluster development and infrastructure")

        # 4. Characteristics & Demographics Facets
        if profile.characteristics:
            c = profile.characteristics
            if c.is_women_owned:
                queries.append("women entrepreneur credit subsidy and financial assistance")
            if c.social_category and c.social_category.value != "general":
                queries.append(f"{c.social_category.value} entrepreneur subsidy margin money assistance")
            if c.is_startup_recognized:
                queries.append("recognized startup credit guarantee scheme DPIIT support")
            if c.is_sustainable:
                queries.append("sustainable zero defect quality certification for MSME")
            if c.is_tech_oriented:
                queries.append("technology upgradation and digital competitiveness MSME")
            if c.exports_currently or c.export_intent:
                queries.append("export promotion marketing assistance procurement support")

        # 5. Core MSME baseline queries
        queries.append("credit linked subsidy for employment generation and micro units")
        queries.append("delayed payments dispute resolution for micro and small enterprises")

        # Deduplicate preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            normalized = " ".join(q.split()).lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_queries.append(q)

        return unique_queries
