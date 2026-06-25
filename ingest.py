
import os, sys, json, logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Make sure project root is on path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.config import Config


def ingest():
    logger.info("=" * 55)
    logger.info("  AneriAI – Resume Ingestion")
    logger.info("=" * 55)

    # ── 1. Check resume exists ─────────────────────────────────
    if not os.path.exists(Config.RESUME_PATH):
        logger.error(f"Resume NOT found at: {Config.RESUME_PATH}")
        logger.error("Please place your PDF there and re-run.")
        sys.exit(1)
    logger.info(f"Resume found: {Config.RESUME_PATH}")

    # ── 2. Load & chunk PDF ────────────────────────────────────
    from app.core.document_loader import DocumentProcessor
    processor = DocumentProcessor()

    logger.info("Loading and chunking resume PDF...")
    chunks = processor.load_resume()
    logger.info(f"✅ {len(chunks)} chunks created")

    # Preview first 3 chunks
    for i, c in enumerate(chunks[:3]):
        logger.info(f"  Chunk {i}: {c[:80].strip()!r}...")

    # ── 3. Clear existing ChromaDB collection ─────────────────
    import chromadb
    from chromadb.config import Settings

    os.makedirs(Config.CHROMA_PERSIST_DIR, exist_ok=True)
    client = chromadb.PersistentClient(
        path=Config.CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    COLLECTION_NAME = "resume_collection"

    # Delete existing collection to start fresh
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Deleted existing collection")
    except Exception:
        pass

    # ── 4. Embed & store ───────────────────────────────────────
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {Config.EMBEDDING_MODEL}")
    embedder = SentenceTransformer(Config.EMBEDDING_MODEL)

    logger.info("Generating embeddings (this may take ~30s)...")
    embeddings = embedder.encode(chunks, show_progress_bar=True).tolist()
    logger.info(f"Embeddings generated: {len(embeddings)} vectors")

    # ── 5. Create collection & add documents ───────────────────
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    def _detect_section(text):
        t = text.lower()
        if any(w in t for w in ['experience', 'work', 'internship', 'engineer']):
            return 'experience'
        if any(w in t for w in ['skill', 'python', 'pytorch', 'tensorflow']):
            return 'skills'
        if any(w in t for w in ['project', 'built', 'developed', 'deployed']):
            return 'projects'
        if any(w in t for w in ['education', 'degree', 'university', 'cgpa']):
            return 'education'
        return 'general'

    metadata = [
        {
            "source":   "resume",
            "chunk_id": i,
            "type":     "professional_info",
            "section":  _detect_section(chunk)
        }
        for i, chunk in enumerate(chunks)
    ]

    ids = [f"doc_{i}" for i in range(len(chunks))]

    # Add in batches of 50
    BATCH = 50
    for start in range(0, len(chunks), BATCH):
        end = min(start + BATCH, len(chunks))
        collection.add(
            embeddings=embeddings[start:end],
            documents=chunks[start:end],
            metadatas=metadata[start:end],
            ids=ids[start:end]
        )
        logger.info(f"  Added batch {start}–{end}")

    total = collection.count()
    logger.info(f"ChromaDB collection '{COLLECTION_NAME}' now has {total} documents")

    # ── 6. Quick similarity test ───────────────────────────────
    logger.info("\nQuick retrieval test: 'What are Aneri skills?'")
    q_embed = embedder.encode("What are Aneri skills?").tolist()
    results = collection.query(
        query_embeddings=[q_embed],
        n_results=3,
        include=["documents", "distances"]
    )
    for i, (doc, dist) in enumerate(zip(
        results['documents'][0], results['distances'][0]
    )):
        logger.info(f"  [{i+1}] score={1-dist:.3f}  {doc[:100].strip()!r}...")

    logger.info("\n" + "=" * 55)
    logger.info("  Ingestion complete! You can now run: python run.py")
    logger.info("=" * 55)


if __name__ == "__main__":
    ingest()
