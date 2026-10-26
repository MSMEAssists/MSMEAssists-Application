"""
Permission & License Advisory Service for MSMEs.

Evaluates statutory registrations, sector licenses, environmental consents,
and municipal clearances required by Indian law based on business profile facts.
"""
from typing import Any, Dict, List, Optional
from app.models.profile_model import ProfileModel
from app.core.constants import RegistrationType, RegistrationStatus


class PermissionLicenseService:
    """Evaluates mandatory permissions and licenses for MSME compliance."""

    def evaluate(
        self,
        profile: Optional[ProfileModel],
        documents: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        biz = profile.business if profile else None
        fin = profile.financial if profile else None
        loc = profile.location if profile else None
        regs = profile.registrations if profile else []

        industry = (biz.industry if biz else "general").lower()
        sub_sector = (biz.sub_sector or "").lower() if biz else ""
        b_type = (biz.type.value if biz else "services").lower()
        employees = fin.employee_count if fin else 0
        state = loc.state if loc else "India"

        # Map existing registrations
        registered_types = {
            r.type.value: r.status.value
            for r in regs
            if hasattr(r, "type") and hasattr(r, "status")
        }

        mandatory_licenses: List[Dict[str, Any]] = []

        # 1. Udyam MSME Registration
        has_udyam = registered_types.get("udyam") in ("registered", "in_progress", "verified")
        mandatory_licenses.append({
            "name": "Udyam MSME Registration",
            "category": "STATUTORY_IDENTITY",
            "authority": "Ministry of Micro, Small and Medium Enterprises",
            "status": "OBTAINED" if has_udyam else "MANDATORY_REQUIRED",
            "legal_basis": "MSMED Act 2006",
            "portal_url": "https://udyamregistration.gov.in/",
            "why_required": "Prerequisite for all central subsidies, collateral-free loans (CGTMSE), and priority credit.",
            "urgency": "IMMEDIATE" if not has_udyam else "COMPLIANT",
        })

        # 2. Goods & Services Tax (GST)
        has_gst = registered_types.get("gst") in ("registered", "in_progress", "verified")
        turnover = fin.annual_turnover_inr if fin else 0
        gst_mandatory = turnover > 2000000 or b_type == "manufacturing" or has_gst
        mandatory_licenses.append({
            "name": "Goods and Services Tax (GSTIN)",
            "category": "TAX_COMPLIANCE",
            "authority": "GST Council & Central Board of Indirect Taxes and Customs (CBIC)",
            "status": "OBTAINED" if has_gst else ("MANDATORY_REQUIRED" if gst_mandatory else "VOLUNTARY"),
            "legal_basis": "CGST Act 2017",
            "portal_url": "https://www.gst.gov.in/",
            "why_required": "Required for inter-state sales, commercial billing, bank credit verification, and input tax credit.",
            "urgency": "IMMEDIATE" if (gst_mandatory and not has_gst) else "COMPLIANT",
        })

        # 3. PAN (Permanent Account Number)
        has_pan = registered_types.get("pan") in ("registered", "in_progress", "verified")
        mandatory_licenses.append({
            "name": "Permanent Account Number (PAN)",
            "category": "TAX_COMPLIANCE",
            "authority": "Income Tax Department of India",
            "status": "OBTAINED" if has_pan else "MANDATORY_REQUIRED",
            "legal_basis": "Income Tax Act 1961",
            "portal_url": "https://www.incometax.gov.in/",
            "why_required": "Core tax identifier for entity operation, bank accounts, and statutory contracts.",
            "urgency": "IMMEDIATE" if not has_pan else "COMPLIANT",
        })

        # 4. Factory License (Factories Act, 1948)
        if b_type == "manufacturing":
            is_factory_threshold = employees >= 10
            mandatory_licenses.append({
                "name": "Factory License & Factory Inspectorate Plan Approval",
                "category": "LABOR_AND_SAFETY",
                "authority": f"Directorate of Factories and Boilers, Govt. of {state}",
                "status": "MANDATORY_REQUIRED" if is_factory_threshold else "EXEMPT_UNDER_THRESHOLD",
                "legal_basis": "The Factories Act 1948 (Section 6 & 7)",
                "portal_url": "https://labour.gov.in/",
                "why_required": (
                    f"Unit has {employees} employees in manufacturing. Factory registration is required "
                    "for units with 10+ workers using power or 20+ workers without power."
                    if is_factory_threshold else
                    f"Unit operates with {employees} workers. Below the 10-worker threshold, but safety standards apply."
                ),
                "urgency": "HIGH" if is_factory_threshold else "MONITOR",
            })

        # 5. State Pollution Control Board Consent (CTE / CTO)
        is_pollution_sensitive = any(
            k in industry or k in sub_sector
            for k in ["metal", "chemical", "textile", "fabrication", "plastics", "paint", "leather", "processing", "manufacturing", "auto"]
        )
        if b_type == "manufacturing" or is_pollution_sensitive:
            mandatory_licenses.append({
                "name": "State Pollution Control Board (SPCB) Consent to Establish (CTE) & Consent to Operate (CTO)",
                "category": "ENVIRONMENTAL_CLEARANCE",
                "authority": f"State Pollution Control Board (SPCB), Govt. of {state}",
                "status": "MANDATORY_REQUIRED",
                "legal_basis": "Water Act 1974 & Air Act 1981",
                "portal_url": "https://cpcb.nic.in/",
                "why_required": f"Manufacturing activities in {industry.title()} produce industrial effluents or emissions requiring categorization (Orange/Green/White category).",
                "urgency": "HIGH",
            })

        # 6. FSSAI License / Registration (Food & Agri businesses)
        is_food = any(
            k in industry or k in sub_sector
            for k in ["food", "agro", "beverage", "bakery", "dairy", "spices", "grain", "restaurant", "edible"]
        )
        if is_food:
            fssai_type = "State / Central License" if turnover > 1200000 else "FSSAI Basic Registration"
            mandatory_licenses.append({
                "name": f"FSSAI Food Safety Registration / License ({fssai_type})",
                "category": "PRODUCT_REGULATION",
                "authority": "Food Safety and Standards Authority of India (FSSAI)",
                "status": "MANDATORY_REQUIRED",
                "legal_basis": "Food Safety and Standards Act 2006",
                "portal_url": "https://foscos.fssai.gov.in/",
                "why_required": "Mandatory prior to manufacturing, handling, packaging, or distributing food items.",
                "urgency": "IMMEDIATE",
            })

        # 7. Municipal Trade License / Shops & Establishment
        mandatory_licenses.append({
            "name": f"Municipal Trade License / Shop & Establishment Act Registration",
            "category": "MUNICIPAL_CLEARANCE",
            "authority": f"Municipal Corporation of {loc.city if loc else 'Local Urban Body'}",
            "status": "MANDATORY_REQUIRED",
            "legal_basis": "State Municipal Corporation Act & Shops and Establishments Act",
            "portal_url": "https://services.india.gov.in/",
            "why_required": "Permits commercial and manufacturing premises to conduct business within urban/rural jurisdictions.",
            "urgency": "HIGH",
        })

        # 8. Fire Safety NOC
        if b_type == "manufacturing" or employees > 15:
            mandatory_licenses.append({
                "name": "Fire Safety Certificate / No Objection Certificate (NOC)",
                "category": "SAFETY_CLEARANCE",
                "authority": f"Fire & Emergency Services Department, Govt. of {state}",
                "status": "MANDATORY_REQUIRED",
                "legal_basis": "National Building Code of India (Part IV - Fire and Life Safety)",
                "portal_url": "https://services.india.gov.in/",
                "why_required": "Ensures industrial shed/premises has adequate fire extinguisher equipment, emergency exits, and water storage.",
                "urgency": "MEDIUM",
            })

        # 9. Import Export Code (IEC)
        is_exporting = (
            profile.characteristics.exports_currently
            or profile.characteristics.export_intent
            if (profile and profile.characteristics)
            else False
        )
        has_iec = registered_types.get("iec") in ("registered", "in_progress", "verified")
        if is_exporting:
            mandatory_licenses.append({
                "name": "Import Export Code (IEC)",
                "category": "FOREIGN_TRADE",
                "authority": "Directorate General of Foreign Trade (DGFT)",
                "status": "OBTAINED" if has_iec else "MANDATORY_REQUIRED",
                "legal_basis": "Foreign Trade (Development and Regulation) Act 1992",
                "portal_url": "https://www.dgft.gov.in/",
                "why_required": "10-digit PAN-linked code mandatory for customs clearance and international export shipments.",
                "urgency": "IMMEDIATE" if not has_iec else "COMPLIANT",
            })

        obtained_count = sum(1 for lic in mandatory_licenses if lic["status"] == "OBTAINED")
        required_count = sum(1 for lic in mandatory_licenses if lic["status"] in ("MANDATORY_REQUIRED", "HIGH", "IMMEDIATE"))

        if required_count == 0:
            overview = "Statutory regulatory compliance is in good standing."
        elif required_count <= 2:
            overview = f"{required_count} statutory permissions require regularization to prevent regulatory scrutiny."
        else:
            overview = f"{required_count} mandatory licenses are missing. Prioritize Udyam, GST, and SPCB clearances."

        return {
            "licenses_held": obtained_count,
            "licenses_required": len(mandatory_licenses),
            "mandatory_licenses": mandatory_licenses,
            "status_overview": overview,
        }
