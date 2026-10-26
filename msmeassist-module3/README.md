# MSMEAssist — Module 3: Explainable AI Recommendation Engine

Part of *An Agentic AI-Powered Intelligent Decision Support Framework for Government Service Intelligence and Sustainable MSME Growth*.

Module 3 is an independent decision-support microservice that generates **transparent, mathematically grounded government scheme recommendations** for Indian MSMEs by combining:
1. **Multi-Perspective Pairwise LLM Comparisons**
2. **The Bradley-Terry-Luce (BTL) Statistical Model**
3. **Minorization-Maximization (MM) Maximum Likelihood Estimation (MLE)**
4. **Feature Attribution & Explainable AI (XAI) Diagnostics**

It consumes MSME business profiles from **Module 1 (Port 8000)** and official government evidence from the **Government Knowledge RAG System (Port 8001)**.

---

## Architecture Diagram

```text
┌──────────────────────────────┐        ┌──────────────────────────────┐
│       Module 1 (Port 8000)   │        │     RAG System (Port 8001)   │
│   MSME Business Profile      │        │   Approved .gov.in Scheme    │
│   (Classification, Turnover, │        │   Evidence, Subsidies,       │
│   Investment, Attributes)    │        │   Criteria & Citations       │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │                                       │
               │ HTTP GET /api/profile/me              │ HTTP POST /api/retrieval/search
               └───────────────────┬───────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    MODULE 3 BACKEND (Port 8002)                      │
│                                                                      │
│   1. Candidate Selection (Top K=5..8 schemes)                        │
│   2. Pairwise Evaluation across all K*(K-1)/2 pairs                  │
│      - Dual-mode: LLM Prompting + Analytical Grounded Fallback       │
│      - Outputs preference probabilities w_ij and rationales          │
│   3. Bradley-Terry-Luce (BTL) Statistical Model                      │
│      P(S_i > S_j) = exp(θ_i) / (exp(θ_i) + exp(θ_j))                 │
│   4. Maximum Likelihood Estimation (MLE) Solver                      │
│      - Hunter (2004) Minorization-Maximization (MM) Algorithm        │
│      - Guaranteed monotonic convergence to optimal latent θ_i        │
│   5. Explainable AI (XAI) Synthesis                                  │
│      - Global & local profile feature attributions (+% impact)       │
│      - Interactive K x K head-to-head tournament win matrix          │
│      - Grounded .gov.in source provenance with page numbers          │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    MODULE 1 FRONTEND (Port 5173)                     │
│   - BTL Latent Utility Rank Ladder (θ_i + preference likelihood bar) │
│   - Interactive Head-to-Head Tournament Matrix (click to inspect)    │
│   - Profile Feature Attribution Chips (+40.9% Women-Owned, etc.)     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Mathematical Formulation

### 1. The Bradley-Terry-Luce (BTL) Model
For a set of $K$ candidate schemes $\{S_1, \dots, S_K\}$, each scheme has a latent utility parameter $\theta_i \in \mathbb{R}$ (where scale parameter $\pi_i = e^{\theta_i} > 0$). The probability that Scheme $i$ is preferred over Scheme $j$ for a specific MSME profile is:

$$P(S_i \succ S_j \mid \text{Profile}) = \frac{\pi_i}{\pi_i + \pi_j} = \frac{1}{1 + e^{-(\theta_i - \theta_j)}} = \sigma(\theta_i - \theta_j)$$

### 2. Maximum Likelihood Estimation via Minorization-Maximization (MM)
Given pairwise preference weights $w_{ij}$ and total comparisons $n_{ij} = w_{ij} + w_{ji}$, parameters $\boldsymbol{\pi}$ are estimated iteratively using the Hunter (2004) Minorization-Maximization algorithm:

$$\pi_i^{(t+1)} = \frac{\sum_{j \neq i} w_{ij} + \epsilon}{\sum_{j \neq i} \frac{n_{ij} + 2\epsilon}{\pi_i^{(t)} + \pi_j^{(t)}}}$$

where $\epsilon > 0$ is a Bayesian Laplace prior that guarantees strong graph connectivity and prevents divergence even with undefeated items. Latent scores are zero-centered: $\theta_i = \ln \pi_i - \frac{1}{K}\sum_k \ln \pi_k$.

---

## Directory Layout

```text
msmeassist-module3/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py             # REST endpoints (/rank, /btl-solve, /health)
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings (ports, CORS, upstream URLs)
│   │   │   └── logging.py            # Structured logging
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── btl_engine.py         # BTL Model & Hunter MM MLE solver
│   │   │   ├── pairwise_evaluator.py # Pairwise evaluator (LLM + analytical fallback)
│   │   │   ├── explainability.py     # Feature attribution & matrix synthesizer
│   │   │   ├── module1_client.py     # Asynchronous client for Module 1 (:8000)
│   │   │   ├── rag_client.py         # Asynchronous client for RAG System (:8001)
│   │   │   └── recommendation_service.py # Master pipeline coordinator
│   │   └── main.py                   # FastAPI app entrypoint
│   ├── tests/
│   │   ├── test_btl_mle.py           # Mathematical convergence & monotonicity tests
│   │   └── test_pipeline.py          # End-to-end integration tests
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
└── README.md
```

---

## How to Run Module 3

### 1. Prerequisites
- Python 3.11+
- Virtual environment with pip

### 2. Setup Virtual Environment
Open a terminal in `msmeassist-module3/backend`:

```powershell
cd msmeassist-module3\backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1
```

*(Note: If you already have an activated virtual environment in the parent workspace, you can use it directly).*

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Configure `.env`
Ensure `.env` exists (already created from `.env.example`):
```powershell
copy .env.example .env
```

Key environment variables:
```env
APP_PORT=8002
MODULE1_BASE_URL=http://localhost:8000
RAG_BASE_URL=http://localhost:8001
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM Mode: offline_analytical | gemini | anthropic | openai
LLM_PROVIDER=offline_analytical
GEMINI_API_KEY=
```
*(Default `LLM_PROVIDER=offline_analytical` requires zero API keys and runs completely offline with full mathematical BTL-MLE execution).*

### 5. Run the Automated Tests
```powershell
pytest tests/ -v
```
Expected output: **7 passed** covering BTL MM convergence, monotonicity, ties, undefeated items, pairwise evaluation, and end-to-end recommendation flow.

### 6. Start the Backend Server
```powershell
uvicorn app.main:app --reload --port 8002
```

The service is now active at:
- **API Base:** `http://localhost:8002`
- **Interactive Swagger Docs:** `http://localhost:8002/docs`
- **Health Check:** `http://localhost:8002/health`

---

## API Reference

### 1. Generate Explainable AI Recommendations
```http
POST /api/recommendations/rank
Content-Type: application/json

{
  "top_k": 5
}
```
**Response includes:**
- `rankings`: Ordered schemes with `rank`, `theta_score`, `win_probability`, `key_comparative_advantage`, `feature_attributions`, and `official_citations`.
- `pairwise_matrix`: $K \times K$ win-rate matrix showing $P(i \succ j)$.
- `pairwise_details`: Individual head-to-head comparison rationales and deciding attributes.
- `feature_importance_summary`: Percentage contribution of profile features (`is_women_owned`, `manufacturing`, `micro`, etc.).

### 2. Standalone BTL Solver
```http
POST /api/recommendations/btl-solve
Content-Type: application/json

{
  "items": ["PMEGP", "CGTMSE", "ZED"],
  "win_matrix": [
    [0.0, 0.8, 0.9],
    [0.2, 0.0, 0.7],
    [0.1, 0.3, 0.0]
  ]
}
```

---

## Full Multi-Module Port Table

| Component | Port | Description |
|---|---|---|
| **Module 1 Frontend** | `http://localhost:5173` | React + Vite User Interface |
| **Module 1 Backend** | `http://localhost:8000` | Profile Onboarding & Eligibility Rules |
| **Module 2 / RAG System** | `http://localhost:8001` | Official Government Knowledge Retrieval & Citations |
| **Module 3 Backend** | `http://localhost:8002` | **Explainable AI Recommendation Engine (BTL + MLE)** |
| **MongoDB** | `localhost:27017` | Profile & user persistence |
