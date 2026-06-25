from flask import Blueprint, jsonify, render_template, request
import logging
import traceback

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

_rag_engine = None
_rag_engine_error = None

def get_rag_engine():
    if _rag_engine is None:
        init_rag_engine(raise_on_error=True)
    return _rag_engine

def init_rag_engine(raise_on_error=False):
    """Called once at app startup to warm up the model."""
    global _rag_engine, _rag_engine_error
    if _rag_engine is not None:
        return _rag_engine

    from app.core.rag_engine import RAGEngine
    logger.info("Pre-loading RAG engine at startup...")
    try:
        _rag_engine = RAGEngine()
        _rag_engine_error = None
        logger.info("RAG engine ready.")
        return _rag_engine
    except Exception as e:
        _rag_engine_error = str(e)
        logger.error(f"RAG engine failed to initialize: {e}\n{traceback.format_exc()}")
        if raise_on_error:
            raise
        return None


@api_bp.route('/')
def index():
    return render_template('index.html')


@api_bp.route('/api/health')
def health():
    try:
        if _rag_engine is None:
            return jsonify({
                "status": "starting" if _rag_engine_error is None else "degraded",
                "message": _rag_engine_error,
                "model": "all-MiniLM-L6-v2"
            }), 200

        engine = _rag_engine
        stats = engine.vector_store.get_collection_stats()
        return jsonify({
            "status": "healthy",
            "knowledge_base_size": stats.get('count', 0),
            "model": "all-MiniLM-L6-v2"
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "degraded",
            "message": _rag_engine_error or str(e)
        }), 200


@api_bp.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400

        question = data['question'].strip()
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400

        if len(question) > 500:
            return jsonify({'error': 'Question too long (max 500 characters)'}), 400

        try:
            engine = get_rag_engine()
        except Exception as e:
            logger.error(f"RAG engine unavailable: {e}")
            return jsonify({
                'error': str(e),
                'response': 'The AI service is not configured yet. Please check the Groq API key and deployment logs.'
            }), 503

        result = engine.generate_response(question)

        return jsonify({
            'response': result.get('response', ''),
            'sources': result.get('sources', []),
            'context_used': result.get('context_used', False)
        })

    except Exception as e:
        logger.error(f"Chat error: {e}\n{traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'response': 'I encountered an error processing your question. Please try again.'
        }), 500
