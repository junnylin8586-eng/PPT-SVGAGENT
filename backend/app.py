"""
Flask Application Entry Point - PPT Agent (Minimal Phase 1)
Clean slate, only what's needed for Phase 1 validation.
"""
import os, sys, logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import event, Engine
import sqlite3

_project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=_project_root / '.env', override=True)

from flask import Flask
from flask_cors import CORS
from models import db
from controllers.ppt_controller import ppt_bp
from controllers.settings_controller import settings_bp
from controllers.chat_controller import chat_bp


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    if not isinstance(dbapi_conn, sqlite3.Connection):
        return
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
    finally:
        cursor.close()


def create_app():
    app = Flask(__name__)

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.environ.get('INSTANCE_DIR') or os.path.join(backend_dir, 'instance')
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, 'ppt_agent.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 1,
        'pool_recycle': 30,
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30,
        },
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    project_root = os.path.dirname(backend_dir)
    upload_folder = os.path.join(project_root, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    CORS(app, origins='*')
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(ppt_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(chat_bp)

    # Health check
    @app.route('/health')
    def health():
        return {'status': 'ok', 'app': 'PPT Agent API'}

    with app.app_context():
        db.create_all()
        # Load persisted settings into app.config
        from models.settings import Settings
        settings = Settings.query.first()
        if settings:
            app.config['AI_PROVIDER_FORMAT'] = settings.ai_provider_format or 'openai'
            if settings.api_key:
                app.config['api_key'] = settings.api_key
            if settings.api_base_url:
                app.config['api_base_url'] = settings.api_base_url
            if settings.text_model:
                app.config['TEXT_MODEL'] = settings.text_model
            if settings.image_model:
                app.config['IMAGE_MODEL'] = settings.image_model
            if settings.minimax_api_key:
                app.config['MINIMAX_API_KEY'] = settings.minimax_api_key
            if settings.minimax_api_base:
                app.config['MINIMAX_API_BASE'] = settings.minimax_api_base
        logging.info('[PPT Agent] Database initialized')

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5031))
    app.run(host='0.0.0.0', port=port, debug=True)
