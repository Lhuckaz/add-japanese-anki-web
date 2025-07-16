from flask import Flask, render_template
from .config import config_by_name
from .routes.main_routes import main
from .routes.api_routes import api

import os

def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    config_name = config_name or os.getenv('FLASK_ENV') or 'development'
    app_config = config_by_name.get(config_name, config_by_name['development'])
    app.config.from_object(app_config)
    app.config.from_pyfile('config.py', silent=True)
    app.register_blueprint(main)
    app.register_blueprint(api)
    register_error_handlers(app)
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
