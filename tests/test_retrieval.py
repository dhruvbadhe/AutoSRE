from app.core.config import settings
from app.services.embedder import embedder
from app.services.vector_store import MultiIndexVectorStore, vector_store

ERROR = "ERR_PGBOUNCER_0x7f3a"

def test_reciprocal_rank_fusion_math():
    dense_results = [
        {"id": "doc-A", "text": "A"},
        {"id": "doc-B", "text": "B"}
    ]
    sparse_results = [
        {"id": "doc-B", "text": "B"},
        {"id": "doc-C", "text": "C"}
    ]
    
    fused = vector_store._reciprocal_rank_fusion(dense_results, sparse_results, k=60)
    
    assert len(fused) == 3
    ids = [d["id"] for d in fused]
    assert "doc-A" in ids
    assert "doc-B" in ids
    assert "doc-C" in ids

def test_multi_index_separation():
    incidents = vector_store.search_incidents("OOMKilled", top_k=2)
    runbooks = vector_store.search_runbooks("OOMKilled", top_k=2)
    
    assert isinstance(incidents, list)
    assert isinstance(runbooks, list)


def test_fresh_store_returns_bm25_only_match_for_exact_error_string(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CHROMA_DB_PATH", str(tmp_path))
    query = f"payment-api {ERROR}"
    query_vec = embedder.embed_query(query)
    far_vec = [0.0] * len(query_vec)
    far_vec[next(i for i in range(1, len(query_vec)) if query_vec[i] == 0)] = 1.0

    # Data a previous process seeded: decoys sit on top of the query in embedding space,
    # the target only shares the exact error token, so dense search alone never ranks it top 3.
    MultiIndexVectorStore().incident_collection.upsert(
        ids=["decoy-1", "decoy-2", "decoy-3", "target"],
        documents=["checkout latency spike", "disk pressure on node", "dns flapping", f"pgbouncer crash {ERROR} on reload"],
        metadatas=[{"service": name} for name in ["checkout-api", "node", "coredns", "pgbouncer"]],
        embeddings=[query_vec, query_vec, query_vec, far_vec],
    )

    fresh = MultiIndexVectorStore()  # what a new API, CLI or eval process builds at import

    assert "target" in [r["id"] for r in fresh.search_incidents(query, top_k=3)]
