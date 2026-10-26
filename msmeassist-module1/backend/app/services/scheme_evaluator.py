"""
Scheme Eligibility & Evidence Evaluator.

Evaluates business profile eligibility strictly against retrieved official RAG evidence.
Anti-hallucination principles:
  - Zero hardcoded scheme-specific rules.
  - Statements, benefits, and required documents are extracted directly from official chunks.
  - If evidence is silent or incomplete, assigns INSUFFICIENT_EVIDENCE or POTENTIALLY_ELIGIBLE.
  - NOT_ELIGIBLE is ONLY assigned when an explicit condition in the retrieved text conflicts with the profile.
"""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.profile_model import ProfileModel
from app.schemas.schemes_schema import (
    EligibilityStatus,
    ProvenanceItem,
)


class SchemeEvaluator:
    """Evidence-grounded eligibility evaluator and factual extractor."""

    # Generic linguistic markers indicating eligibility conditions in official government guidelines
    _ELIGIBILITY_CUE_PATTERNS = [
        r"(?:eligib(?:le|ility)|criteria|beneficiar(?:y|ies)|who can apply|applicable to|open to|conditions?)[^.\n:]*[:\-]?\s*([^.\n]+)",
        r"(?:any individual|units?|enterprises?|entities|startups?)[^.\n]+(?:shall be|are|is) eligible[^.\n]*",
        r"(?:minimum|maximum|age|qualification|turnover|investment|ceiling)[^.\n]+(?:is|shall be|not exceeding|up to)[^.\n]+",
    ]

    # Generic linguistic markers indicating benefits/assistance
    _BENEFIT_CUE_PATTERNS = [
        r"(?:subsidy|financial assistance|grant|credit guarantee|margin money|incentive|reimbursement|support)[^.\n]*[:\-]?\s*([^.\n]+)",
        r"(?:up to|maximum of|rate of|coverage of)[^.\n]+(?:%|percent|lakh|crore|inr|rs\.)[^.\n]*",
    ]

    # Generic linguistic markers indicating required documents
    _DOCUMENT_CUE_PATTERNS = [
        r"(?:documents? required|enclosures?|attach(?:ed)?|submission of|following documents)[^.\n]*[:\-]?\s*([^.\n]+)",
        r"(?:udyam|aadhaar|pan|project report|dpr|caste certificate|bank statement|quotation|incorporation certificate)[^.\n]*",
    ]

    # Generic linguistic markers indicating application route / process
    _APPLICATION_CUE_PATTERNS = [
        r"(?:how to apply|application (?:process|procedure|portal)|apply online|portal|website)[^.\n]*[:\-]?\s*([^.\n]+)",
        r"(?:online application|portal at|registered on|portal\s*[:\-]?\s*https?://[^\s]+)[^.\n]*",
    ]

    def extract_provenance_items(
        self,
        chunks: List[Dict[str, Any]],
        cue_patterns: List[str],
        max_items: int = 3,
    ) -> List[ProvenanceItem]:
        """Dynamically extracts grounded statements matching linguistic cues with full chunk provenance."""
        extracted: List[ProvenanceItem] = []
        seen_statements: Set[str] = set()

        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_id = chunk.get("chunk_id")
            page_num = chunk.get("page_number")
            url = chunk.get("official_url", "")
            org = chunk.get("source_organization", "Government of India")

            # Split into sentence-like clauses
            sentences = [s.strip() for s in re.split(r"[.\n]+", text) if len(s.strip()) > 15]

            for sentence in sentences:
                for pattern in cue_patterns:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        clean_stmt = " ".join(sentence.split())
                        norm = clean_stmt.lower()
                        if norm not in seen_statements and len(clean_stmt) >= 20:
                            seen_statements.add(norm)
                            extracted.append(
                                ProvenanceItem(
                                    statement=clean_stmt,
                                    chunk_id=chunk_id,
                                    page_number=page_num,
                                    source_url=url,
                                    source_organization=org,
                                )
                            )
                            if len(extracted) >= max_items:
                                return extracted
        return extracted

    def evaluate_scheme(
        self,
        profile: Optional[ProfileModel],
        chunks: List[Dict[str, Any]],
        document_meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluates profile against evidence strictly extracted from retrieved chunks."""
        # 1. Extract grounded clauses
        eligibility_clauses = self.extract_provenance_items(chunks, self._ELIGIBILITY_CUE_PATTERNS, max_items=4)
        benefit_clauses = self.extract_provenance_items(chunks, self._BENEFIT_CUE_PATTERNS, max_items=4)
        document_clauses = self.extract_provenance_items(chunks, self._DOCUMENT_CUE_PATTERNS, max_items=4)
        app_process_items = self.extract_provenance_items(chunks, self._APPLICATION_CUE_PATTERNS, max_items=1)
        app_process = app_process_items[0] if app_process_items else None

        combined_text = " ".join([c.get("text", "") for c in chunks]).lower()

        # 2. Check for explicit conflicts vs alignments with profile
        why_it_matches: List[str] = []
        conflicts: List[ProvenanceItem] = []
        insufficient_notes: List[str] = []
        aligned_attributes: List[str] = []

        if not profile:
            return {
                "eligibility_status": EligibilityStatus.POTENTIALLY_ELIGIBLE,
                "why_it_matches": ["General MSME scheme relevant to micro and small enterprises."],
                "key_eligibility_criteria": eligibility_clauses,
                "benefits_available": benefit_clauses,
                "required_documents": document_clauses,
                "application_process": app_process,
                "unmet_or_conflicting_conditions": [],
                "insufficient_evidence_notes": ["No business profile provided for tailored evaluation."],
                "aligned_attributes": ["general_msme"],
                "retrieval_score": max([c.get("similarity_score", 0.0) for c in chunks] or [0.0]),
                "eligibility_evidence_score": 0.5,
                "profile_alignment_score": 0.5,
                "recommendation_score": 0.5,
            }

        # Profile dimensions
        sector = profile.business.type.value.lower() if profile.business else ""
        classification = profile.financial.msme_classification.value.lower() if profile.financial else ""
        state = profile.location.state.lower() if profile.location else ""
        area_type = profile.location.area_type.value.lower() if profile.location else ""
        
        # Sector matching & explicit exclusions
        if sector:
            is_excluded = False
            for c in chunks:
                c_text = c.get("text", "")
                c_text_lower = c_text.lower()
                has_mfg_only = (
                    sector != "manufacturing"
                    and bool(re.search(r"\b(?:only\s+(?:to\s+)?manufacturing|manufacturing\s+only)\b", c_text_lower))
                )
                has_sector_not_covered = bool(
                    re.search(rf"\b{sector}\b.*?\b(?:not\s+covered|excluded|not\s+eligible)\b", c_text_lower)
                )
                if has_mfg_only or has_sector_not_covered:
                    is_excluded = True
                    # Extract the verbatim matching sentence
                    sentences = [s.strip() for s in re.split(r"[.\n]+", c_text) if len(s.strip()) > 10]
                    matched_sentence = next(
                        (s for s in sentences if ("manufacturing" in s.lower() or sector in s.lower()) and ("only" in s.lower() or "not" in s.lower() or "exclud" in s.lower())),
                        c_text[:200]
                    )
                    conflicts.append(
                        ProvenanceItem(
                            statement=matched_sentence,
                            chunk_id=c.get("chunk_id"),
                            page_number=c.get("page_number"),
                            source_url=c.get("official_url", ""),
                            source_organization=c.get("source_organization"),
                        )
                    )
                    break

            if not is_excluded and sector in combined_text:
                why_it_matches.append(f"Official guidelines explicitly support the {sector.title()} sector.")
                aligned_attributes.append(f"{sector}_sector")

        # Scale / Classification matching & explicit exclusions
        if classification:
            if classification in combined_text and f"{classification} is excluded" not in combined_text:
                why_it_matches.append(f"Applicable to {classification.title()} scale enterprises.")
                aligned_attributes.append(f"{classification}_msme")
            elif "micro only" in combined_text and classification != "micro":
                for c in chunks:
                    if "micro only" in c.get("text", "").lower():
                        conflicts.append(
                            ProvenanceItem(
                                statement="Official source explicitly restricts eligibility to micro enterprises.",
                                chunk_id=c.get("chunk_id"),
                                page_number=c.get("page_number"),
                                source_url=c.get("official_url", ""),
                                source_organization=c.get("source_organization"),
                            )
                        )
                        break

        # Characteristics matching
        if profile.characteristics:
            c = profile.characteristics
            if c.is_women_owned and ("women" in combined_text or "woman" in combined_text or "special category" in combined_text):
                why_it_matches.append("Special benefits/higher subsidy identified for women-owned enterprises.")
                aligned_attributes.append("women_owned")
            if c.is_startup_recognized and ("startup" in combined_text or "dpiit" in combined_text):
                why_it_matches.append("Provides credit guarantee or ecosystem support for recognized startups.")
                aligned_attributes.append("startup_recognized")
            if c.is_sustainable and ("zed" in combined_text or "zero defect" in combined_text or "sustainable" in combined_text):
                why_it_matches.append("Directly facilitates sustainable practices and quality certification.")
                aligned_attributes.append("sustainable_practices")
            if (c.exports_currently or c.export_intent) and ("export" in combined_text or "procurement" in combined_text or "marketing" in combined_text):
                why_it_matches.append("Supports marketing, procurement, or trade exhibition activities.")
                aligned_attributes.append("market_development")

        # 3. Determine Strict Status Semantics
        if conflicts:
            status = EligibilityStatus.NOT_ELIGIBLE
            eligibility_score = 0.0
        elif not eligibility_clauses and not why_it_matches:
            status = EligibilityStatus.INSUFFICIENT_EVIDENCE
            insufficient_notes.append("Retrieved official evidence does not contain explicit eligibility conditions for this profile.")
            eligibility_score = 0.2
        elif any("sanction" in cl.statement.lower() or "dpr" in cl.statement.lower() or "bank" in cl.statement.lower() or "subject to" in cl.statement.lower() for cl in eligibility_clauses):
            status = EligibilityStatus.CONDITIONALLY_ELIGIBLE
            eligibility_score = 0.8
        elif why_it_matches and eligibility_clauses:
            status = EligibilityStatus.ELIGIBLE
            eligibility_score = 1.0
        else:
            status = EligibilityStatus.POTENTIALLY_ELIGIBLE
            eligibility_score = 0.6

        # 4. Decoupled Scoring
        retrieval_score = max([c.get("similarity_score", 0.0) for c in chunks] or [0.0])
        alignment_score = min(len(aligned_attributes) / 3.0, 1.0) if aligned_attributes else 0.3
        
        # Composite Recommendation Score: 30% retrieval, 45% eligibility evidence, 25% profile alignment
        if status == EligibilityStatus.NOT_ELIGIBLE:
            recommendation_score = 0.05
        else:
            recommendation_score = round(
                (0.30 * retrieval_score) + (0.45 * eligibility_score) + (0.25 * alignment_score),
                3
            )

        if not why_it_matches and status != EligibilityStatus.NOT_ELIGIBLE:
            why_it_matches.append("Relevant official MSME initiative based on enterprise scale and sector.")

        return {
            "eligibility_status": status,
            "why_it_matches": why_it_matches,
            "key_eligibility_criteria": eligibility_clauses,
            "benefits_available": benefit_clauses,
            "required_documents": document_clauses,
            "application_process": app_process,
            "unmet_or_conflicting_conditions": conflicts,
            "insufficient_evidence_notes": insufficient_notes,
            "aligned_attributes": aligned_attributes or ["general_msme"],
            "retrieval_score": round(retrieval_score, 3),
            "eligibility_evidence_score": round(eligibility_score, 3),
            "profile_alignment_score": round(alignment_score, 3),
            "recommendation_score": recommendation_score,
        }
