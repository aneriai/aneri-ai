# AneriAI - Professional Assistant Chatbot

A Flask RAG chatbot that answers questions about Aneri Bhavsar's professional background using a ChromaDB knowledge base, Sentence Transformers embeddings, and the Groq API.

## Features

- Resume and portfolio-aware chat responses
- Retrieval-Augmented Generation with ChromaDB
- Groq-hosted LLM responses
- Flask API with a responsive HTML/CSS/JavaScript chat UI
- Health endpoint for deployment checks
- Free Render deployment configuration

## Tech Stack

- Backend: Flask, Gunicorn
- LLM: Groq API
- Vector database: ChromaDB
- Embeddings: Sentence Transformers (`all-MiniLM-L6-v2`)
- Frontend: HTML, CSS, JavaScript
- Deployment: Render Free Web Service

## Local Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create your local environment file.

```bash
copy .env.example .env
```

4. Add your Groq key to `.env`.

```env
GROQ_API_KEY=your_real_groq_key
```

5. Run the app.

```bash
python run.py
```

Open `http://localhost:5000`.

## Deploy Free On Render

Render supports free Python web services. Free services sleep after about 15 minutes without traffic and wake up on the next request, so the first portfolio visitor after idle time may wait around a minute.

1. Push this repository to GitHub.

2. Go to [Render](https://dashboard.render.com/) and choose **New > Blueprint**.

3. Connect the GitHub repository that contains this project. Render will read `render.yaml`.

4. When Render asks for secret values, paste your Groq API key for:

```text
GROQ_API_KEY
```

5. Deploy the service.

After the build finishes, Render gives you a URL like:

```text
https://aneri-ai.onrender.com
```

Use that URL in your portfolio.

## Manual Render Settings

If you choose **New > Web Service** instead of Blueprint, use these values:

- Runtime: `Python`
- Instance type: `Free`
- Build command: `pip install --upgrade pip && pip install -r requirements.txt && python preload_model.py`
- Start command: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload`
- Health check path: `/api/health`
- Python version: `3.11.11`

Environment variables:

```text
GROQ_API_KEY=your_real_groq_key
SECRET_KEY=generate-any-long-random-string
LLM_MODEL=llama-3.1-8b-instant
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./vector_db/chroma_db
SENTENCE_TRANSFORMERS_HOME=/opt/render/project/src/.cache/sentence-transformers
HF_HOME=/opt/render/project/src/.cache/huggingface
```

## Useful Endpoints

- `/` - Chat UI
- `/api/chat` - POST chat endpoint
- `/api/health` - Deployment health check

## Notes

- Do not commit `.env`; it is intentionally ignored by Git.
- The existing ChromaDB files are included in the repository so the free deployment does not need persistent disk storage.
- If you update the resume or knowledge base PDFs, run `python ingest.py`, then commit the updated `vector_db` files.
