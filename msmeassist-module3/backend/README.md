# Module 3 Backend — Quick Reference

FastAPI backend for **Explainable AI Recommendation Engine** using Pairwise LLM Comparisons, the Bradley-Terry-Luce (BTL) Model, and Maximum Likelihood Estimation (MLE).

## Quick Start

```powershell
# 1. Activate environment
.\venv\Scripts\Activate.ps1

# 2. Install requirements
python -m pip install -r requirements.txt

# 3. Run automated tests
pytest tests/ -v

# 4. Start the backend on port 8002
uvicorn app.main:app --reload --port 8002
```

## Endpoints

- **Swagger Documentation:** http://localhost:8002/docs
- **Health Check:** http://localhost:8002/health
- **Recommendations:** `POST /api/recommendations/rank`
- **BTL Solver:** `POST /api/recommendations/btl-solve`

See `../README.md` for full mathematical formulation, architecture diagrams, and system integration details.
