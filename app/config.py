import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""

    # Groq API
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

    # Flask 
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    PORT       = int(os.getenv('PORT', 5000))

    # Models 
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    LLM_MODEL       = os.getenv('LLM_MODEL', 'llama-3.1-8b-instant')  
    TEMPERATURE     = float(os.getenv('TEMPERATURE', 0.3))
    MAX_TOKENS      = int(os.getenv('MAX_TOKENS', 512))  

    # Paths
    BASE_DIR             = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

 
    _chroma_env          = os.getenv('CHROMA_PERSIST_DIR', './vector_db/chroma_db')
    CHROMA_PERSIST_DIR   = _chroma_env if os.path.isabs(_chroma_env) \
                           else os.path.join(BASE_DIR, _chroma_env.lstrip('./').lstrip('../'))

    RESUME_PATH          = os.path.join(BASE_DIR, 'data', 'raw', 'Resume_Aneri Bhavsar.pdf')
    KNOWLEDGE_BASE_PATH  = os.path.join(BASE_DIR, 'data', 'raw', 'Aneri_Knowledge_Base.pdf')
    PROCESSED_DATA_PATH  = os.path.join(BASE_DIR, 'data', 'processed', 'chunks.json')

    os.makedirs(os.path.join(BASE_DIR, 'data', 'raw'),       exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'data', 'processed'), exist_ok=True)
    os.makedirs(CHROMA_PERSIST_DIR,                           exist_ok=True)