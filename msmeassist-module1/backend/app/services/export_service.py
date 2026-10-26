"""
Export & Global Trade Agent Service

Comprehensive logic for calculating export readiness scores, evaluating official DGFT
and Ministry of Commerce export schemes (RoDTEP, Interest Equalization, MAI, EPCG),
auditing mandatory export licenses (IEC, RCMC, GST LUT), and generating customs checklists.
"""
import logging
from typing import Any, Dict, List, Optional
from app.models.profile_model import ProfileModel
from app.schemas.export_schema import (
    DocumentChecklistItem,
    ExportAdvisoryResponse,
    ExportReadinessScore,
    ExportRequest,
    ExportSchemeItem,
    LicenseAuditItem,
)

logger = logging.getLogger(__name__)


def _extract_facts(profile: Optional[ProfileModel], documents: Optional[List[Any]] = None) -> Dict[str, Any]:
    biz = profile.business if profile else None
    fin = profile.financial if profile else None
    loc = profile.location if profile else None
    char = profile.characteristics if profile else None

    registered_types = set()
    if profile and getattr(profile, "registrations", None):
        for r in profile.registrations:
            rstat = getattr(r, "status", None)
            sval = rstat.value if hasattr(rstat, "value") else (str(rstat) if rstat else "")
            rtype = getattr(r, "type", None)
            tval = rtype.value if hasattr(rtype, "value") else (str(rtype) if rtype else "")
            if sval == "registered" and tval:
                registered_types.add(tval.lower())

    docs_uploaded = set()
    if documents:
        for d in documents:
            dtype = getattr(d, "document_type", None)
            dval = dtype.value if hasattr(dtype, "value") else (str(dtype) if dtype else "")
            dstat = getattr(d, "status", None)
            sval = dstat.value if hasattr(dstat, "value") else (str(dstat) if dstat else "uploaded")
            if dval and sval in ("uploaded", "verified"):
                docs_uploaded.add(dval.lower())

    msme_cls = "micro"
    if fin and getattr(fin, "msme_classification", None):
        cls_val = fin.msme_classification
        msme_cls = cls_val.value if hasattr(cls_val, "value") else str(cls_val)

    return {
        "business_name": biz.name if (biz and getattr(biz, "name", None)) else "Your Enterprise",
        "msme_classification": msme_cls,
        "industry": biz.industry if (biz and getattr(biz, "industry", None)) else "Manufacturing & General Trade",
        "state": loc.state if (loc and getattr(loc, "state", None)) else "India",
        "annual_turnover_inr": fin.annual_turnover_inr if (fin and getattr(fin, "annual_turnover_inr", None)) else None,
        "exports_currently": char.exports_currently if (char and getattr(char, "exports_currently", None) is not None) else False,
        "export_intent": char.export_intent if (char and getattr(char, "export_intent", None) is not None) else True,
        "is_startup_recognized": char.is_startup_recognized if (char and getattr(char, "is_startup_recognized", None) is not None) else False,
        "registered_types": registered_types,
        "docs_uploaded": docs_uploaded,
    }


def assess_export_advisory(
    request: ExportRequest,
    profile: Optional[ProfileModel],
    documents: Optional[List[Any]] = None,
) -> ExportAdvisoryResponse:
    facts = _extract_facts(profile, documents)
    regs = facts["registered_types"]
    docs = facts["docs_uploaded"]

    # Combined industry / sector string from profile and optional request payload
    combined_industry = f"{facts['industry'] or ''} {request.product_category or ''}".lower()

    # Overrides from request if provided, otherwise check registrations and uploaded documents
    has_iec = (
        request.has_iec
        if request.has_iec is not None
        else ("iec" in regs or "import export code" in regs or any("iec" in d for d in docs))
    )
    has_rcmc = (
        request.has_rcmc
        if request.has_rcmc is not None
        else ("rcmc" in regs or any("rcmc" in d for d in docs))
    )
    has_udyam = "udyam" in regs or any("udyam" in d for d in docs)
    has_gst = "gst" in regs or "gstin" in regs or any("gst" in d for d in docs)
    has_fssai = (
        "fssai" in regs
        or any("fssai" in d for d in docs)
        or ("food" in combined_industry or "agri" in combined_industry)
    )

    # 1. READINESS SCORECARD
    score = 0
    strengths = []
    gaps = []

    if has_udyam:
        score += 20
        strengths.append("Official Udyam MSME Registration verified")
    else:
        gaps.append("Missing Udyam Registration certificate")

    if has_gst:
        score += 20
        strengths.append("Active GSTIN for tax compliance & export refunds")
    else:
        gaps.append("GST Registration missing for export tax zero-rating")

    if has_iec:
        score += 25
        strengths.append("Import Export Code (IEC) registered with DGFT")
    else:
        gaps.append("Import Export Code (IEC) not registered on DGFT portal")

    if has_rcmc:
        score += 15
        strengths.append("RCMC Certificate active with Export Promotion Council")
    else:
        gaps.append("RCMC registration missing from Export Promotion Council (FIEO/APEDA)")

    if facts["exports_currently"] or facts["export_intent"]:
        score += 20
        strengths.append("Active Export Intent & Product Readiness signal")

    if score >= 75:
        level = "High Export Readiness"
        summary = "Your enterprise satisfies core DGFT and customs prerequisites for international export!"
    elif score >= 45:
        level = "Moderate Readiness — Action Items Required"
        summary = "Your business has strong MSME fundamentals, but missing export licenses (IEC/RCMC) require attention."
    else:
        level = "Beginning Export Journey"
        summary = "Complete your basic DGFT registrations and obtain an Import Export Code (IEC) to begin exporting."

    readiness = ExportReadinessScore(
        score=score,
        level=level,
        summary=summary,
        strengths=strengths,
        gaps=gaps,
    )

    # 2. SCHEMES
    schemes = [
        ExportSchemeItem(
            id="rodtep",
            title="RoDTEP Scheme (Remission of Duties and Taxes on Exported Products)",
            organization="Directorate General of Foreign Trade (DGFT) / Ministry of Commerce",
            category="Tax Rebate",
            benefit_description="Reimburses un-refunded central, state, and local duties/taxes paid on inputs used in export goods.",
            estimated_benefit="0.5% to 4.3% refund on FOB Export Value",
            eligibility_status="eligible" if has_iec else "action_needed",
            official_url="https://www.dgft.gov.in",
            what_to_do="File RoDTEP claims automatically in your Shipping Bill at ICEGATE portal using your IEC Code.",
        ),
        ExportSchemeItem(
            id="ies",
            title="Interest Equalization Scheme (IES) for Export Credit",
            organization="Reserve Bank of India (RBI) / Ministry of Commerce",
            category="Financial Credit Subsidy",
            benefit_description="Provides 3% to 5% interest rate subvention on pre-shipment and post-shipment rupee export credit for MSMEs.",
            estimated_benefit="3% to 5% Interest Rate Discount on Export Bank Loans",
            eligibility_status="eligible" if (has_udyam and has_iec) else "action_needed",
            official_url="https://www.rbi.org.in",
            what_to_do="Apply through your regular commercial bank submitting your Udyam Certificate & IEC code.",
        ),
        ExportSchemeItem(
            id="mai",
            title="Market Access Initiative (MAI) Scheme",
            organization="Department of Commerce, Govt. of India",
            category="Market Development Grant",
            benefit_description="Financial support for overseas trade fairs, buyer-seller meets, international exhibition stalls, and market studies.",
            estimated_benefit="Up to 50% - 75% Reimbursement on Stall Costs & Airfare",
            eligibility_status="eligible" if has_rcmc else "action_needed",
            official_url="https://commerce.gov.in",
            what_to_do="Submit application through your designated Export Promotion Council (e.g. FIEO or APEDA).",
        ),
        ExportSchemeItem(
            id="epcg",
            title="Export Promotion Capital Goods (EPCG) Scheme",
            organization="DGFT / Ministry of Commerce",
            category="Customs Duty Exemption",
            benefit_description="Allows import of capital goods/machinery for pre-production, production, and post-production at 0% customs duty.",
            estimated_benefit="100% Customs Duty Relief on Capital Machinery Import",
            eligibility_status="eligible" if has_iec else "action_needed",
            official_url="https://www.dgft.gov.in",
            what_to_do="Apply for EPCG License on DGFT portal prior to importing capital equipment.",
        ),
    ]

    if "textile" in combined_industry or "apparel" in combined_industry or "garment" in combined_industry:
        schemes.append(
            ExportSchemeItem(
                id="rosctl",
                title="RoSCTL Scheme (Rebate of State and Central Taxes and Levies)",
                organization="Ministry of Textiles / DGFT",
                category="Tax Rebate",
                benefit_description="Special tax rebate scheme exclusively for apparel, garments, and made-up textile exports.",
                estimated_benefit="Up to 6.05% Rebate on FOB Export Value",
                eligibility_status="eligible" if has_iec else "action_needed",
                official_url="https://texmin.nic.in",
                what_to_do="Claim rebate via Duty Credit Scrips issued electronically at ICEGATE portal.",
            )
        )

    # 3. LICENSES AUDIT
    licenses = [
        LicenseAuditItem(
            name="Import Export Code (IEC)",
            authority="Directorate General of Foreign Trade (DGFT)",
            status="met" if has_iec else "missing",
            profile_value="Registered IEC on file" if has_iec else "Not registered",
            description="10-digit mandatory registration required for any commercial import/export operation in India.",
            how_to_fix="Apply online at www.dgft.gov.in with PAN, Bank Details, and Aadhaar OTP. Issued instantly.",
            portal_url="https://www.dgft.gov.in",
        ),
        LicenseAuditItem(
            name="Registration Cum Membership Certificate (RCMC)",
            authority="Export Promotion Council (FIEO / APEDA / Spice Board / EEPC)",
            status="met" if has_rcmc else "missing",
            profile_value="Active RCMC Membership" if has_rcmc else "Not on file",
            description="Mandatory certificate to avail export concessions under Foreign Trade Policy (FTP) and MAI grants.",
            how_to_fix="Register on the e-RCMC module at DGFT portal by selecting your relevant Export Promotion Council.",
            portal_url="https://www.dgft.gov.in",
        ),
        LicenseAuditItem(
            name="GST Letter of Undertaking (LUT)",
            authority="Central Board of Indirect Taxes and Customs (CBIC)",
            status="met" if has_gst else "needs_verification",
            profile_value="GSTIN Registered" if has_gst else "GST Missing",
            description="Allows export of goods/services without paying IGST upfront, preserving cash flow.",
            how_to_fix="File Form GST RFD-11 annually on the GST Portal (www.gst.gov.in) before commencing exports.",
            portal_url="https://www.gst.gov.in",
        ),
    ]

    if has_fssai or "food" in combined_industry or "agri" in combined_industry:
        licenses.append(
            LicenseAuditItem(
                name="FSSAI Central Export License / APEDA Registration",
                authority="FSSAI / APEDA",
                status="met" if has_fssai else "missing",
                profile_value="FSSAI Registered" if has_fssai else "Pending",
                description="Mandatory food safety export license required for exporting agricultural or food items.",
                how_to_fix="Apply for FSSAI Central License on FoSCoS portal (foscos.fssai.gov.in).",
                portal_url="https://foscos.fssai.gov.in",
            )
        )

    # 4. DOCUMENTS CHECKLIST
    documents_checklist = [
        DocumentChecklistItem(
            document_name="Import Export Code (IEC) Certificate",
            stage="Pre-Shipment",
            mandatory=True,
            status="ready" if has_iec else "pending",
            description="Official DGFT registration document authorizing international trade.",
        ),
        DocumentChecklistItem(
            document_name="Commercial Invoice & Packing List",
            stage="Customs Clearance",
            mandatory=True,
            status="ready",
            description="Detailed bill specifying product breakdown, HS codes, unit prices, and packaging metrics.",
        ),
        DocumentChecklistItem(
            document_name="Certificate of Origin (CoO)",
            stage="Customs Clearance",
            mandatory=True,
            status="pending",
            description="Proves goods originated in India to claim preferential tariff discounts in destination countries.",
        ),
        DocumentChecklistItem(
            document_name="Shipping Bill / Bill of Export",
            stage="Customs Clearance",
            mandatory=True,
            status="pending",
            description="Customs document filed at ICEGATE portal prior to loading cargo on vessel/aircraft.",
        ),
        DocumentChecklistItem(
            document_name="Electronic Bank Realization Certificate (e-BRC)",
            stage="Post-Shipment",
            mandatory=True,
            status="pending",
            description="Issued by bank upon receiving foreign currency payment; required for government tax refunds.",
        ),
    ]

    portals = [
        {"name": "DGFT Portal", "url": "https://www.dgft.gov.in", "purpose": "IEC Code, e-RCMC, EPCG & RoDTEP Licenses"},
        {"name": "ICEGATE Customs Portal", "url": "https://www.icegate.gov.in", "purpose": "Shipping Bill Tracking & Duty Scrips"},
        {"name": "Indian Trade Portal", "url": "https://www.indiantradeportal.in", "purpose": "HS Codes, Foreign Tariffs & Trade Agreements"},
        {"name": "FIEO Export Portal", "url": "https://www.fieo.org", "purpose": "Federation of Indian Export Organisations Guidance"},
    ]

    return ExportAdvisoryResponse(
        business_name=facts["business_name"],
        msme_classification=facts["msme_classification"],
        industry=facts["industry"],
        state=facts["state"],
        readiness=readiness,
        schemes=schemes,
        licenses=licenses,
        documents=documents_checklist,
        disclaimer="Export guidance and incentive estimates are based on Foreign Trade Policy (FTP 2023) guidelines. Final duty drawback, RoDTEP scrips, and customs clearances are subject to DGFT & CBIC verification.",
        official_portals=portals,
    )
