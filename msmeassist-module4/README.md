# Module 4: Finance & Loan Agent

**MSMEAssist — Intelligent Financial Analysis and Loan Advisory Engine**

---

## Purpose

Module 4 provides a complete Finance & Loan Advisory Agent for MSMEs. It analyses an MSME's financial position, identifies funding gaps, retrieves relevant government loan schemes via the existing RAG knowledge base, consumes the BTL-ranked recommendations produced by Module 3, and delivers structured, explainable loan advisory output.

The agent acts as an **advisor**, not a lender. All final loan approvals, interest rates, and sanctioned amounts are determined by the respective financial institution or government authority.

---

## Architecture

```
Module 1 (Business Profile)
        │  auth token / profile data
        ▼
Module 4 FinanceLoanAgentOrchestrator
        │
        ├─► FinancialAnalyzer
        │       Revenue · Expenses · Profit · DSCR
        │       Cash Flow · Funding Gap · Health Score
        │
        ├─► RagIntegrationService ◄─── RAG System (Port 8001)
        │       Loan schemes · Eligibility · Documents
        │       Interest rates · Tenure · CGTMSE · MUDRA
        │
        ├─► Module3IntegrationService ◄─ Module 3 (Port 8002)
        │       BTL-ranked scheme priorities
        │
        └─► LoanAdvisor
                Loan requirement identification
                Eligibility evaluation
                Option ranking & scoring
                Explainable recommendation synthesis
                        │
                        ▼
                LoanAdvisoryResponse (JSON)
```

---

## Folder Structure

```
msmeassist-module4/
└── backend/
    ├── .env                        Runtime environment variables
    ├── .env.example                Template for environment setup
    ├── requirements.txt            Python dependencies
    ├── pytest.ini                  pytest configuration (asyncio_mode=auto)
    ├── app/
    │   ├── main.py                 FastAPI entrypoint (port 8004)
    │   ├── api/
    │   │   └── routes.py           REST API endpoints
    │   ├── core/
    │   │   └── config.py           Pydantic settings (loaded from .env)
    │   ├── models/
    │   │   └── schemas.py          Request / Response Pydantic schemas
    │   └── services/
    │       ├── agent_orchestrator.py   Master orchestrator
    │       ├── financial_analyzer.py   Revenue / DSCR / health scoring
    │       ├── loan_advisor.py         Loan categorisation & ranking
    │       ├── rag_integration.py      RAG retrieval client
    │       ├── module1_client.py       Module 1 profile fetch client
    │       └── module3_integration.py  Module 3 BTL ranking client
    └── tests/
        ├── test_financial_analyzer.py
        ├── test_loan_advisor.py
        └── test_agent_orchestrator.py
```

---

## Inputs

### Financial Inputs (`FinancialInputs`)

| Field | Type | Description |
|---|---|---|
| `annual_turnover_inr` | float | Annual revenue in INR |
| `monthly_revenue_inr` | float | Monthly revenue in INR |
| `monthly_expenses_inr` | float | Monthly operating expenses in INR |
| `existing_liabilities_inr` | float | Outstanding loan balance in INR |
| `existing_monthly_emi_inr` | float | Current monthly EMI in INR |
| `working_capital_requirement_inr` | float | Working capital needed |
| `investment_requirement_inr` | float | Machinery / expansion capex needed |
| `available_capital_inr` | float | Liquid savings / reserve |
| `credit_score` | int | CIBIL / credit score (300–900) |
| `has_existing_loan` | bool | Whether existing loan is active |
| `profitability_status` | str | `profitable` / `break_even` / `loss` |

Missing fields are detected and flagged in `missing_information`. The agent never fabricates values; it clearly states which data was estimated and why.

### Loan Inputs (`LoanInputs`)

| Field | Type | Description |
|---|---|---|
| `requested_amount_inr` | float | Desired loan amount |
| `purpose` | str | Working Capital / Machinery / Expansion |
| `preferred_loan_type` | str | Preferred category |
| `max_acceptable_interest_rate` | float | Max acceptable rate % |
| `preferred_tenure_months` | int | Preferred tenure |

### Business Profile (`BusinessProfilePayload`)

| Field | Type | Description |
|---|---|---|
| `name` | str | Business name |
| `business_type` | str | manufacturing / service / trading |
| `industry` | str | Industry sector |
| `business_age_years` | float | Years in operation |
| `msme_classification` | str | micro / small / medium |
| `state` | str | State of operation |
| `is_women_owned` | bool | Women-owned enterprise |
| `social_category` | str | general / sc / st / obc |
| `is_rural_enterprise` | bool | Rural location flag |
| `is_startup_recognized` | bool | DPIIT startup recognition |

---

## Outputs

### `POST /api/finance/analyze` — `FinancialAnalysisResponse`

```json
{
  "financial_summary": {
    "annual_revenue": "₹50.00 Lakh",
    "monthly_revenue": "₹4.17 Lakh",
    "monthly_expenses": "₹3.13 Lakh",
    "monthly_profit": "₹1.04 Lakh",
    "net_cash_flow": "₹0.84 Lakh",
    "existing_liabilities": "₹5.00 Lakh",
    "working_capital_requirement": "₹6.25 Lakh",
    "investment_requirement": "₹0",
    "available_capital": "₹0",
    "funding_requirement": "₹6.25 Lakh",
    "gross_margin_pct": 25.0,
    "estimated_dscr": 2.61,
    "repayment_capacity_rating": "HIGH",
    "financial_health_score": 85
  },
  "financial_risks": [],
  "missing_information": ["Monthly revenue not explicitly specified; derived from annual turnover."],
  "improvement_areas": ["Maintain clear Udyam and GST filing records..."],
  "analysis_explanation": "The business generates an estimated annual turnover of ₹50.00 Lakh..."
}
```

### `POST /api/finance/loan-recommendation` — `LoanAdvisoryResponse`

```json
{
  "business_name": "Sunrise Textiles",
  "msme_classification": "Micro",
  "financial_summary": { "...": "..." },
  "loan_requirement": {
    "required_amount": "₹15.00 Lakh",
    "raw_amount_inr": 1500000.0,
    "purpose": "Working Capital & Equipment",
    "loan_type": "MSME Government-Supported Loan",
    "urgency": "MODERATE"
  },
  "recommended_options": [
    {
      "id": "rag_loan_1",
      "name": "CGTMSE Collateral-Free Credit Guarantee Scheme",
      "type": "Credit Guarantee-linked Financing",
      "category": "Credit Guarantee-linked financing",
      "reason": "Option recommended for Sunrise Textiles because...",
      "eligibility": "Registered Micro Enterprise operating in Maharashtra.",
      "amount": "Up to ₹2.00 Crore",
      "interest_rate": "8.5% - 11.5% p.a. (Bank & Scheme dependent)",
      "tenure": "3 to 7 Years",
      "documents": ["Udyam Registration Certificate", "PAN Card & Aadhaar", "..."],
      "financial_suitability_score": 0.94,
      "btl_rank": 1,
      "source_organization": "Ministry of MSME & SIDBI",
      "official_url": "https://www.cgtmse.in/"
    }
  ],
  "financial_risks": [],
  "missing_information": [],
  "improvement_areas": [],
  "explanation": "Based on financial analysis of Sunrise Textiles...",
  "disclaimer": "Final loan approval, interest rate, sanctioned amount, and eligibility are determined solely by the respective bank, financial institution, or government authority."
}
```

---

## APIs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/finance/analyze` | Standalone financial analysis |
| `POST` | `/api/finance/loan-recommendation` | Full loan advisory workflow |
| `GET` | `/api/finance/options` | Supported loan categories list |
| `GET` | `/api/finance/health` | Health check |
| `GET` | `/` | Root alive check |

All endpoints return structured JSON. Errors return `{ "detail": "..." }` with an appropriate HTTP status code.

---

## RAG Integration

Module 4 calls the RAG knowledge base to retrieve real government loan scheme data rather than hard-coding arbitrary figures. The retrieval strategy is:

1. **In-process call** — if Module 4 is co-hosted with the RAG system in a unified FastAPI app, the retrieval service is called directly in memory with zero network overhead.
2. **HTTP call** — `POST {RAG_SERVICE_URL}/api/retrieval/search` with the generated query and `top_k`.
3. **Curated fallback corpus** — five well-known official schemes (CGTMSE, PMEGP, MUDRA, SIDBI Equipment Loan, Stand-Up India) with verified `.gov.in` URLs are used when the RAG service is offline or returns no results. This ensures the agent never fabricates information.

The RAG query is automatically constructed from the business profile and loan requirement:

```
"MSME loan financial scheme {purpose} collateral free credit guarantee
 {msme_class} enterprise {state}"
```

---

## Module 3 Integration

Module 4 consumes the BTL-ranked scheme output from Module 3's Explainable AI Recommendation Engine:

1. **In-process call** — if running inside the same process, `RecommendationService.generate_recommendations()` is called directly.
2. **HTTP call** — `POST {MODULE3_SERVICE_URL}/api/recommendations/rank` with a constructed profile dict.
3. **Graceful degradation** — if Module 3 is unavailable, Module 4 falls back to RAG-only ranking without failing.

The BTL rank and `final_score` from Module 3 influence the `financial_suitability_score` on each `RecommendedLoanOption`, ensuring financial suitability and scheme relevance are jointly considered.

---

## Module 1 Integration

When an `Authorization: Bearer <token>` header is passed to `POST /api/finance/loan-recommendation`, Module 4:

1. Tries to decode the JWT and fetch the user's `Profile` document from MongoDB directly (in-process).
2. Falls back to `GET {MODULE1_SERVICE_URL}/api/profile/me` over HTTP.
3. Merges the fetched business and financial data with any values the caller already supplied (caller values take precedence).

The field mapping from Module 1 (`investment_inr`) to Module 4 (`investment_requirement_inr`) is handled transparently in `module1_client.py`.

---

## Agent Workflow

```
1. Resolve Profile
   └─ JWT decode → MongoDB lookup (in-process)
   └─ HTTP GET /api/profile/me (fallback)
   └─ Request payload (caller override)

2. Financial Analysis (FinancialAnalyzer)
   ├─ Derive missing values with documented assumptions
   ├─ Compute: monthly profit, gross margin, DSCR, debt ratio
   ├─ Score: financial health (0–100)
   ├─ Rate: repayment capacity (HIGH / MODERATE / CONSTRAINED / LOW)
   └─ Identify: risks, missing info, improvement areas

3. Loan Requirement Identification (LoanAdvisor)
   ├─ Determine required amount (requested or funding gap)
   ├─ Classify purpose and loan type
   └─ Set urgency flag

4. RAG Retrieval (RagIntegrationService)
   └─ Retrieve up to top_k relevant loan / scheme records

5. Module 3 BTL Rankings (Module3IntegrationService)
   └─ Fetch pairwise-ranked scheme priorities (optional)

6. Eligibility Evaluation & Ranking (LoanAdvisor)
   ├─ Categorise each RAG scheme (CGTMSE / MUDRA / Term Loan / etc.)
   ├─ Map BTL rank if available
   ├─ Adjust financial_suitability_score by repayment capacity
   ├─ Add standard fallback options if RAG returns < 3 results
   └─ Sort by financial_suitability_score descending

7. Explanation Synthesis (Orchestrator)
   └─ Build plain-language advisory paragraph from actual data

8. Return LoanAdvisoryResponse
```

---

## Example Request

```bash
curl -X POST http://localhost:8004/api/finance/loan-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "financial_inputs": {
      "annual_turnover_inr": 5000000,
      "monthly_expenses_inr": 320000,
      "existing_liabilities_inr": 500000,
      "working_capital_requirement_inr": 700000,
      "investment_requirement_inr": 1000000
    },
    "loan_inputs": {
      "requested_amount_inr": 1500000,
      "purpose": "Machinery Purchase and Working Capital"
    },
    "business_profile": {
      "name": "Sunrise Textiles",
      "business_type": "manufacturing",
      "industry": "Textile",
      "business_age_years": 4.0,
      "msme_classification": "micro",
      "state": "Maharashtra",
      "is_women_owned": true
    },
    "use_module3_rankings": true,
    "top_k": 5
  }'
```

---

## Running Module 4

### 1. Set up virtual environment

```bash
cd msmeassist-module4/backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env   # Windows
# or
cp .env.example .env     # Linux / macOS
# Edit .env to point to your Module 1, RAG, and Module 3 service URLs
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8004
```

API docs available at: `http://localhost:8004/docs`

---

## Testing

```bash
cd msmeassist-module4/backend
pytest
```

### Test coverage

| Test file | What it covers |
|---|---|
| `test_financial_analyzer.py` | Revenue/expense/profit calculations, DSCR, risk detection, missing-data handling |
| `test_loan_advisor.py` | Loan requirement identification, option ranking, BTL score integration |
| `test_agent_orchestrator.py` | Full orchestrator async workflow, all four API endpoints, edge cases |

---

## How Module 4 Connects to Modules 1–3

| Connection | Direction | What flows |
|---|---|---|
| Module 1 → Module 4 | Pull (JWT / HTTP) | Business name, type, industry, MSME classification, state, annual turnover, investment, loan flags |
| RAG System → Module 4 | Pull (in-process / HTTP) | Loan scheme chunks: name, eligibility, amount, interest, tenure, documents, URL |
| Module 3 → Module 4 | Pull (in-process / HTTP) | BTL-ranked scheme list with `theta_score` and `win_probability` |
| Module 4 → User | Push (REST JSON) | Financial analysis, loan requirement, ranked options, risks, explanation, disclaimer |

None of Modules 1, 2, or 3 are modified. Module 4 is a pure consumer of their outputs.

---

## Disclaimer

Module 4 is an advisory tool only. Final loan approval, sanctioned amount, interest rate, and eligibility determination rest solely with the respective bank, NBFC, or government authority.
