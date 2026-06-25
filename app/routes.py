from flask import Blueprint, jsonify, render_template, request
import logging
import traceback

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# Lazy-load RAG engine to avoid import-time errors
_rag_engine = None

def get_rag_engine():
    global _rag_engine
    if _rag_engine is None:
        from app.core.rag_engine import RAGEngine
        _rag_engine = RAGEngine()
    return _rag_engine


@api_bp.route('/')
def index():
    return render_template('index.html')


@api_bp.route('/api/health')
def health():
    try:
        engine = get_rag_engine()
        stats = engine.vector_store.get_collection_stats()
        return jsonify({
            "status": "healthy",
            "knowledge_base_size": stats.get('count', 0),
            "model": "gemini-2.0-flash-exp"
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


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

        engine = get_rag_engine()
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