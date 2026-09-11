import httpx
from typing import List
from app.core.config import settings

class GeminiEmbedder:
    def __init__(self):
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
        self.headers = {"Content-Type": "application/json"}

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        batch_size = 16
        all_embeddings = []

        with httpx.Client(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                requests_payload = [
                    {
                        "model": "models/gemini-embedding-001",
                        "content": {"parts": [{"text": text}]}
                    }
                    for text in batch
                ]
                url = f"{self.api_url}?key={settings.GEMINI_API_KEY}"
                response = client.post(
                    url,
                    headers=self.headers,
                    json={"requests": requests_payload}
                )
                response.raise_for_status()
                data = response.json()

                for emb_obj in data.get("embeddings", []):
                    all_embeddings.append(emb_obj.get("values", []))
                    
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        embeddings = self.embed_documents([text])
        return embeddings[0] if embeddings else []

embedder = GeminiEmbedder()