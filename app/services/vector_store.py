import os
import chromadb
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from app.core.config import settings
from app.services.embedder import embedder

class MultiIndexVectorStore:
    def __init__(self):
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

        self.incident_collection = self.client.get_or_create_collection(
            name="incident_logs",
            metadata={"hnsw:space": "cosine"}
        )
        self.runbook_collection = self.client.get_or_create_collection(
            name="runbooks",
            metadata={"hnsw:space": "cosine"}
        )

        # Rebuilt from what is already on disk, so every process (API, CLI, eval) gets hybrid search, not just the seed script.
        self.incident_corpus, self.incident_bm25 = self._load_bm25(self.incident_collection)
        self.runbook_corpus, self.runbook_bm25 = self._load_bm25(self.runbook_collection)

    @staticmethod
    def _load_bm25(collection):
        data = collection.get(include=["documents", "metadatas"])
        corpus = [
            {"id": doc_id, "document": document, "metadata": metadata}
            for doc_id, document, metadata in zip(data["ids"], data["documents"], data["metadatas"])
        ]
        bm25 = BM25Okapi([item["document"].lower().split() for item in corpus]) if corpus else None
        return corpus, bm25

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        scores = {}
        doc_map = {}

        # Equal weights (standard RRF): with the old 0.7/0.3 split a BM25-only hit (0.3/61) could never beat
        # the 3rd dense hit (0.7/63), so exact error-string matches were dropped by the top_k cut.
        for rank, item in enumerate(dense_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            doc_map[doc_id] = item

        for rank, item in enumerate(sparse_results):
            doc_id = item["id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = item

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [doc_map[doc_id] for doc_id in sorted_ids]

    def add_incidents(self, incidents: List[Dict[str, Any]]):
        if not incidents:
            return

        ids = [inc["id"] for inc in incidents]
        documents = [f"{inc['service']} {inc['error_type']} {inc['log_snippet']} {inc.get('root_cause', '')}" for inc in incidents]
        metadatas = [
            {
                "service": inc["service"],
                "error_type": inc["error_type"],
                "root_cause": inc.get("root_cause", ""),
                "severity": inc.get("severity", "ERROR")
            }
            for inc in incidents
        ]

        embeddings = embedder.embed_documents(documents)
        self.incident_collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        self.incident_corpus, self.incident_bm25 = self._load_bm25(self.incident_collection)

    def add_runbooks(self, runbooks: List[Dict[str, Any]]):
        if not runbooks:
            return

        ids = [rb["id"] for rb in runbooks]
        documents = [f"{rb['title']} {rb['service']} {rb['procedure']} {rb['command_snippet']}" for rb in runbooks]
        metadatas = [
            {
                "title": rb["title"],
                "service": rb["service"],
                "command_snippet": rb.get("command_snippet", "")
            }
            for rb in runbooks
        ]

        embeddings = embedder.embed_documents(documents)
        self.runbook_collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

        self.runbook_corpus, self.runbook_bm25 = self._load_bm25(self.runbook_collection)

    def search_incidents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query_embedding = embedder.embed_query(query)
        dense_raw = self.incident_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        dense_results = []
        if dense_raw and dense_raw["ids"] and dense_raw["ids"][0]:
            for i in range(len(dense_raw["ids"][0])):
                dense_results.append({
                    "id": dense_raw["ids"][0][i],
                    "document": dense_raw["documents"][0][i],
                    "metadata": dense_raw["metadatas"][0][i]
                })

        sparse_results = []
        if self.incident_bm25:
            tokens = query.lower().split()
            scores = self.incident_bm25.get_scores(tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            # A zero BM25 score means no shared token, so it is not a lexical match.
            sparse_results = [self.incident_corpus[idx] for idx in top_indices if scores[idx] > 0]

        return self._reciprocal_rank_fusion(dense_results, sparse_results)[:top_k]

    def search_runbooks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        query_embedding = embedder.embed_query(query)
        dense_raw = self.runbook_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        dense_results = []
        if dense_raw and dense_raw["ids"] and dense_raw["ids"][0]:
            for i in range(len(dense_raw["ids"][0])):
                dense_results.append({
                    "id": dense_raw["ids"][0][i],
                    "document": dense_raw["documents"][0][i],
                    "metadata": dense_raw["metadatas"][0][i]
                })

        sparse_results = []
        if self.runbook_bm25:
            tokens = query.lower().split()
            scores = self.runbook_bm25.get_scores(tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            sparse_results = [self.runbook_corpus[idx] for idx in top_indices if scores[idx] > 0]

        return self._reciprocal_rank_fusion(dense_results, sparse_results)[:top_k]

vector_store = MultiIndexVectorStore()