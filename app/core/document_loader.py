import os
import json
import logging
from typing import List
from app.config import Config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Load the resume PDF and split it into text chunks."""

    CHUNK_SIZE    = 500
    CHUNK_OVERLAP = 60

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Simple recursive text splitter — no langchain dependency needed."""
        separators = ["\n\n", "\n", ". ", " ", ""]
        chunks = []

        def split_with_sep(txt, seps):
            if len(txt) <= chunk_size:
                stripped = txt.strip()
                if stripped:
                    chunks.append(stripped)
                return
            sep = seps[0] if seps else ""
            rest = seps[1:] if seps else []
            parts = txt.split(sep) if sep else list(txt)
            current = ""
            for part in parts:
                candidate = current + (sep if current else "") + part
                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    # overlap
                    overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = overlap_text + (sep if overlap_text else "") + part
                    if len(current) > chunk_size and rest:
                        split_with_sep(current, rest)
                        current = ""
            if current.strip():
                chunks.append(current.strip())

        split_with_sep(text, separators)
        return chunks

    def load_resume(self) -> List[str]:
        """Load PDF and return list of clean text chunks."""
        if not os.path.exists(Config.RESUME_PATH):
            raise FileNotFoundError(
                f"Resume not found at: {Config.RESUME_PATH}\n"
                "Please place the PDF there."
            )

        logger.info(f"Loading PDF: {Config.RESUME_PATH}")

        try:
            from pypdf import PdfReader

            reader_resume = PdfReader(Config.RESUME_PATH)
            pages_text = []
            for i, page in enumerate(reader_resume.pages):
                text = page.extract_text() or ""
                pages_text.append(text)
            
            if hasattr(Config, 'KNOWLEDGE_BASE_PATH') and os.path.exists(Config.KNOWLEDGE_BASE_PATH):
                logger.info(f"Loading PDF: {Config.KNOWLEDGE_BASE_PATH}")
                reader_kb = PdfReader(Config.KNOWLEDGE_BASE_PATH)
                for i, page in enumerate(reader_kb.pages):
                    text = page.extract_text() or ""
                    pages_text.append(text)

            full_text = "\n".join(pages_text)
            logger.info(f"Loaded pages from PDF(s)")

            # Simple recursive text splitter (no langchain needed)
            chunks = self._split_text(full_text, self.CHUNK_SIZE, self.CHUNK_OVERLAP)
            logger.info(f"Split into {len(chunks)} chunks")

            # Cache chunks
            os.makedirs(os.path.dirname(Config.PROCESSED_DATA_PATH), exist_ok=True)
            with open(Config.PROCESSED_DATA_PATH, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            logger.info(f"Chunks cached → {Config.PROCESSED_DATA_PATH}")

            return chunks

        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            raise RuntimeError(
                "pypdf or langchain not installed.\n"
                "Run: pip install pypdf langchain"
            ) from e

    def get_processed_chunks(self) -> List[str]:
        """Return cached chunks if available, else re-process."""
        if os.path.exists(Config.PROCESSED_DATA_PATH):
            try:
                with open(Config.PROCESSED_DATA_PATH, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                logger.info(f"Loaded {len(chunks)} chunks from cache")
                return chunks
            except Exception as e:
                logger.warning(f"Cache read failed: {e} — re-processing PDF")
        return self.load_resume()