import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
from app.config import Config
import os
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """Manage ChromaDB vector database operations."""

    COLLECTION_NAME = "resume_collection"

    def __init__(self):
        logger.info("Initializing VectorStore...")

        # Embedding model
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        logger.info(f"Embedding model loaded: {Config.EMBEDDING_MODEL}")

        # ChromaDB client (persistent)
        os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PERSIST_DIR)
        self.collection = self._get_or_create_collection()
        logger.info(f"ChromaDB ready | collection: {self.COLLECTION_NAME} | docs: {self.collection.count()}")

    # ──────────────────────────────────────────────────────────────
    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(self.COLLECTION_NAME)
        except Exception:
            logger.info("Creating new ChromaDB collection...")
            return self.client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

    # ──────────────────────────────────────────────────────────────
    def add_documents(self, texts: List[str], metadata: List[Dict] = None):
        if not texts:
            logger.warning("No texts to add — skipping")
            return

        logger.info(f"Embedding and adding {len(texts)} documents...")

        embeddings = self.embedding_model.encode(
            texts, show_progress_bar=True
        ).tolist()

        if metadata is None:
            metadata = [{"source": f"chunk_{i}"} for i in range(len(texts))]

        ids = [f"doc_{i}" for i in range(len(texts))]

        # Add in batches to avoid memory issues
        BATCH = 50
        for start in range(0, len(texts), BATCH):
            end = min(start + BATCH, len(texts))
            self.collection.add(
                embeddings=embeddings[start:end],
                documents=texts[start:end],
                metadatas=metadata[start:end],
                ids=ids[start:end]
            )

        logger.info(f"✅ Added {len(texts)} documents. Total: {self.collection.count()}")

    # ──────────────────────────────────────────────────────────────
    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        try:
            query_embedding = self.embedding_model.encode(query).tolist()

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, self.collection.count() or 1),
                include=["documents", "metadatas", "distances"]
            )

            docs      = results.get('documents', [[]])[0]
            metas     = results.get('metadatas',  [[]])[0]
            distances = results.get('distances',  [[]])[0]

            return [
                {
                    'text':            doc,
                    'metadata':        meta,
                    'relevance_score': round(1 - dist, 4)
                }
                for doc, meta, dist in zip(docs, metas, distances)
            ]

        except Exception as e:
            logger.error(f"Similarity search error: {e}")
            return []

    # ──────────────────────────────────────────────────────────────
    def get_collection_stats(self) -> Dict:
        try:
            return {
                'collection_name': self.COLLECTION_NAME,
                'count':           self.collection.count()
            }
        except Exception:
            return {'collection_name': self.COLLECTION_NAME, 'count': 0}