import sqlite3
import json

con = sqlite3.connect(r"rag-system\backend\data\gov_rag.db")
cur = con.cursor()
cur.execute("""
    SELECT d.document_id, json_extract(d.data, '$.title') as title, json_extract(d.data, '$.url') as url
    FROM documents d
    WHERE json_extract(d.data, '$.title') LIKE '%CGTMSE%'
       OR json_extract(d.data, '$.title') LIKE '%Credit Guarantee%'
       OR json_extract(d.data, '$.url') LIKE '%cgtmse%'
""")
rows = cur.fetchall()
print(f"Found {len(rows)} CGTMSE/Credit Guarantee documents:")
for r in rows:
    print(f" - {r[0]}: {r[1]} -> {r[2]}")
