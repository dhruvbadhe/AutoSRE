import pytest
from app.services.vector_store import vector_store

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