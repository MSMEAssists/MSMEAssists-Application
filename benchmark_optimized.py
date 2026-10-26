import time
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def get_auth_token(client):
    unique_id = int(time.time() * 1000) % 100000000
    mobile = f"+9199{unique_id:08d}"
    email = f"perf_{unique_id}@example.com"
    
    reg_payload = {
        "full_name": "Perf Test User",
        "email": email,
        "mobile_number": mobile,
        "password": "Password123",
        "confirm_password": "Password123"
    }
    r = client.post("/api/auth/register", json=reg_payload)
    if r.status_code == 201:
        return r.json().get("access_token")
    print(f"[Auth Register Error]: {r.status_code} - {r.text}")
    return None

def run_benchmarks():
    print("=================================================================")
    print(" MSMEAssist Performance Benchmark — Full System Performance Run")
    print("=================================================================")
    
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health
        try:
            r = client.get("/health")
            print(f"[Health Check] Status: {r.status_code}, Response: {r.json()}")
        except Exception as e:
            print(f"[Health Check Failed]: {e}")
            return

        # 2. Authenticate
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        print(f"[Auth] Token acquired: {bool(token)}")

        # 3. RAG Retrieval Search (Module 2)
        rag_payload = {"query": "PMEGP subsidy eligibility criteria manufacturing", "top_k": 5}
        t0 = time.perf_counter()
        r_rag = client.post("/api/retrieval/search", json=rag_payload)
        t_rag1 = (time.perf_counter() - t0) * 1000
        rag_data = r_rag.json()
        rag_count = len(rag_data) if isinstance(rag_data, list) else len(rag_data.get('results', []))
        print(f"[1. RAG Search (First Call)] Status: {r_rag.status_code}, Latency: {t_rag1:.2f} ms, Results: {rag_count}")

        t0 = time.perf_counter()
        r_rag2 = client.post("/api/retrieval/search", json=rag_payload)
        t_rag2 = (time.perf_counter() - t0) * 1000
        print(f"[1. RAG Search (Cached Call)] Status: {r_rag2.status_code}, Latency: {t_rag2:.2f} ms")

        # 4. Schemes Discovery (GET /api/schemes/discovery)
        t0 = time.perf_counter()
        r_disc = client.get("/api/schemes/discovery", headers=headers)
        t_disc1 = (time.perf_counter() - t0) * 1000
        disc_count = len(r_disc.json().get('schemes', [])) if r_disc.status_code == 200 else 0
        print(f"[2. Schemes Discovery (First Call)] Status: {r_disc.status_code}, Latency: {t_disc1:.2f} ms, Schemes: {disc_count}")

        t0 = time.perf_counter()
        r_disc2 = client.get("/api/schemes/discovery", headers=headers)
        t_disc2 = (time.perf_counter() - t0) * 1000
        print(f"[2. Schemes Discovery (Cached Call)] Status: {r_disc2.status_code}, Latency: {t_disc2:.2f} ms")

        # 5. Chat Assistant (POST /api/schemes/query)
        chat_payload = {"query": "What are the eligibility criteria for PMEGP subsidy?"}
        t0 = time.perf_counter()
        r_chat = client.post("/api/schemes/query", json=chat_payload, headers=headers)
        t_chat1 = (time.perf_counter() - t0) * 1000
        chat_data = r_chat.json() if r_chat.status_code == 200 else {}
        print(f"[3. Chat Assistant (First Call)] Status: {r_chat.status_code}, Latency: {t_chat1:.2f} ms, Citations: {len(chat_data.get('citations', []))}")

        t0 = time.perf_counter()
        r_chat2 = client.post("/api/schemes/query", json=chat_payload, headers=headers)
        t_chat2 = (time.perf_counter() - t0) * 1000
        print(f"[3. Chat Assistant (Cached Call)] Status: {r_chat2.status_code}, Latency: {t_chat2:.2f} ms")

        # 6. Module 3 Recommendations (POST /api/recommendations/rank)
        rec_payload = {"top_k": 5}
        t0 = time.perf_counter()
        r_rec = client.post("/api/recommendations/rank", json=rec_payload, headers=headers)
        t_rec1 = (time.perf_counter() - t0) * 1000
        rec_data = r_rec.json() if r_rec.status_code == 200 else {}
        print(f"[4. Module 3 BTL Recommendations (First Call)] Status: {r_rec.status_code}, Latency: {t_rec1:.2f} ms, Rankings: {len(rec_data.get('rankings', []))}")

        t0 = time.perf_counter()
        r_rec2 = client.post("/api/recommendations/rank", json=rec_payload, headers=headers)
        t_rec2 = (time.perf_counter() - t0) * 1000
        print(f"[4. Module 3 BTL Recommendations (Cached Call)] Status: {r_rec2.status_code}, Latency: {t_rec2:.2f} ms")

        # 7. Compliance Agent (POST /api/compliance/scheme-check)
        comp_payload = {
            "scheme_id": "pmegp_subsidy",
            "scheme_name": "Prime Minister Employment Generation Programme (PMEGP)",
            "scheme_organization": "Ministry of MSME / KVIC",
            "knowledge_type": "SUBSIDY"
        }
        t0 = time.perf_counter()
        r_comp = client.post("/api/compliance/scheme-check", json=comp_payload, headers=headers)
        t_comp1 = (time.perf_counter() - t0) * 1000
        comp_data = r_comp.json() if r_comp.status_code == 200 else {}
        print(f"[5. Compliance Agent (First Call)] Status: {r_comp.status_code}, Latency: {t_comp1:.2f} ms, Rules: {len(comp_data.get('rules', []))}, Gaps: {len(comp_data.get('gaps', []))}")

        t0 = time.perf_counter()
        r_comp2 = client.post("/api/compliance/scheme-check", json=comp_payload, headers=headers)
        t_comp2 = (time.perf_counter() - t0) * 1000
        print(f"[5. Compliance Agent (Cached Call)] Status: {r_comp2.status_code}, Latency: {t_comp2:.2f} ms")

        # 8. Master Decision Intelligence Orchestration (POST /api/decision-intelligence/orchestrate)
        dec_payload = {
            "objective": "scheme_subsidy",
            "top_k": 5,
            "target_state": "Karnataka"
        }
        t0 = time.perf_counter()
        r_dec = client.post("/api/decision-intelligence/orchestrate", json=dec_payload, headers=headers)
        t_dec1 = (time.perf_counter() - t0) * 1000
        dec_data = r_dec.json() if r_dec.status_code == 200 else {}
        summary = dec_data.get("decision_summary", {})
        statuses = dec_data.get("orchestration_status", {})
        print(f"[6. Master Decision Orchestrator (First Call)] Status: {r_dec.status_code}, Latency: {t_dec1:.2f} ms, Internal: {summary.get('total_orchestration_time_ms')} ms")
        for k, v in statuses.items():
            print(f"   -> Agent '{v.get('agent_name')}': {v.get('latency_ms')} ms ({v.get('status')})")

        t0 = time.perf_counter()
        r_dec2 = client.post("/api/decision-intelligence/orchestrate", json=dec_payload, headers=headers)
        t_dec2 = (time.perf_counter() - t0) * 1000
        print(f"[6. Master Decision Orchestrator (Cached Call)] Status: {r_dec2.status_code}, Latency: {t_dec2:.2f} ms")

    print("=================================================================")

if __name__ == "__main__":
    run_benchmarks()
