"""
Web interface server for Comfy Gimpy Studio.
"""

import logging
import asyncio
from flask import Flask
from flask_cors import CORS

from .api import templates_bp
from ..shared.config import load_config

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Enable CORS
    CORS(app)

    # Load configuration
    config = load_config()

    # Register blueprints
    app.register_blueprint(templates_bp)

    # Basic health check endpoint
    @app.route('/health')
    def health():
        return {"status": "healthy", "service": "comfy-gimpy-studio"}

    # Root endpoint
    @app.route('/')
    def index():
        return {
            "service": "Comfy Gimpy Studio Web Interface",
            "version": "1.0",
            "endpoints": {
                "templates": "/api/templates",
                "health": "/health"
            }
        }

    logger.info("Web interface application created")
    return app


def run_server(host: str = "localhost", port: int = 5000, debug: bool = False):
    """Run the web server."""
    app = create_app()

    logger.info(f"Starting web server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # Run with default settings
    run_server()