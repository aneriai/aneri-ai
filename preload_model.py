#!/usr/bin/env python3
"""
Pre-downloads the sentence-transformers model at build time
so the app doesn't timeout downloading it on first request.
"""
import os
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
print(f"[build] Pre-downloading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
print(f"[build] ✅ Model downloaded and cached successfully.")
