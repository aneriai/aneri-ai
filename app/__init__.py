import os
import logging
from flask import Flask

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s – %(message)s'
)
def create_app():
    base_dir      = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    templates_dir = os.path.join(base_dir, 'templates')
    # Static files live inside the app package
    static_dir    = os.path.join(os.path.dirname(__file__), 'static')

    app = Flask(
        __name__,
        template_folder=templates_dir,
        static_folder=static_dir,
        static_url_path='/static'
    )

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

    from app.routes import api_bp, init_rag_engine
    app.register_blueprint(api_bp)

    # Pre-load the RAG engine (model + ChromaDB) at startup
    with app.app_context():
        init_rag_engine()

    return app