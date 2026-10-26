"""
Module 4 FastAPI Main Entrypoint.
Run independently with: uvicorn app.main:app --port 8004
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="MSMEAssist Module 4: Finance & Loan Agent",
    description="Intelligent financial analysis and loan advisory engine for MSMEs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "MSMEAssist Module 4 Finance & Loan Agent is active"}
